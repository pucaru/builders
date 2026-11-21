"""Derive test impact from patches and maps of the clean checkout."""
import ast
from functools import lru_cache
import gzip
import json
import re

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def sections(patch):
    files = []
    for line in patch.splitlines(keepends=True):
        if line.startswith("diff --git "):
            paths = line.rstrip("\n").removeprefix("diff --git ").split(" b/", 1)
            if len(paths) != 2 or not paths[0].startswith("a/"):
                raise ValueError("unsupported filename")
            files.append((paths[0][2:], paths[1], []))
        elif files:
            files[-1][2].append(line)
    if not files:
        raise ValueError("no git diff sections")
    return files


def apply_hunks(source, patch):
    """Reconstruct one Python file in memory and verify every context line."""
    old = source.splitlines(keepends=True)
    output = []
    cursor = remaining = added = 0
    started = False
    for index, raw in enumerate(patch):
        if raw.startswith("@@"):
            match = HUNK.match(raw)
            if not match or remaining or added:
                raise ValueError("invalid hunk")
            position, remaining, added = (int(match[1]), int(match[2] or 1),
                                          int(match[4] or 1))
            position -= bool(remaining)
            if not cursor <= position <= len(old):
                raise ValueError("invalid hunk position")
            output.extend(old[cursor:position])
            cursor, started = position, True
            continue
        if not started:
            if not raw.startswith(("index ", "--- ", "+++ ")):
                raise ValueError("structural diff")
            continue
        if raw.startswith("\\ No newline"):
            continue
        if not raw or raw[0] not in " +-":
            raise ValueError("invalid hunk line")
        line = raw[1:]
        if index + 1 < len(patch) and patch[index + 1].startswith("\\ No newline"):
            line = line.removesuffix("\n")
        if raw[0] in " -":
            if not remaining or cursor >= len(old) or old[cursor] != line:
                raise ValueError("hunk context mismatch")
            cursor += 1
            remaining -= 1
        if raw[0] in " +":
            if not added:
                raise ValueError("invalid addition count")
            output.append(line)
            added -= 1
    if not started or remaining or added:
        raise ValueError("incomplete diff")
    output.extend(old[cursor:])
    return "".join(output)


class FunctionBodies(ast.NodeTransformer):
    def __init__(self):
        self.bodies = []

    def visit_FunctionDef(self, node):
        docstring = ast.get_docstring(node, clean=False)
        # Yield and docstrings can be observable without executing a body.
        generator = self.contains_yield(node)
        first = node.body[0].lineno
        last = node.body[-1].end_lineno
        fingerprint = tuple(ast.dump(statement) for statement in node.body)
        self.bodies.append((first, last, fingerprint))
        node.body = [ast.Constant(docstring), ast.Constant(generator)]
        return node

    @staticmethod
    def contains_yield(node):
        pending = list(node.body)
        while pending:
            child = pending.pop()
            if isinstance(child, (ast.Yield, ast.YieldFrom)):
                return True
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                                      ast.ClassDef)):
                pending.extend(ast.iter_child_nodes(child))
        return False

    visit_AsyncFunctionDef = visit_FunctionDef


def body_shape(source):
    tree = ast.parse(source)
    visitor = FunctionBodies()
    visitor.visit(tree)
    return ast.dump(tree), visitor.bodies


baseline_shape = lru_cache(maxsize=16)(body_shape)


def changed_bodies(source, patched):
    old_shape, old_bodies = baseline_shape(source)
    new_shape, new_bodies = body_shape(patched)
    if old_shape != new_shape or len(old_bodies) != len(new_bodies):
        return None
    return [(first, last) for (first, last, old_body), (_, _, new_body)
            in zip(old_bodies, new_bodies) if old_body != new_body]


def replacement_statements(source, patched, hunk):
    """Find simple old statements replaced line-for-line by this patch.

    An insertion, deletion, or changed compound header needs the wider
    function-level selection. The diff has already been applied and checked.
    """
    tree = ast.parse(source)
    new_tree = ast.parse(patched)
    # A new local binding can change an earlier read into UnboundLocalError,
    # even when control flow never reaches the edited assignment.
    def bindings(t):
        return sorted((type(n.ctx).__name__, n.id) for n in ast.walk(t)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)))
    if bindings(tree) != bindings(new_tree):
        return None
    changed = []
    old_line = None
    removed = added = 0
    for raw in hunk:
        match = HUNK.match(raw) if raw.startswith("@@") else None
        if match:
            if removed != added:
                return None
            old_line = int(match[1])
            removed = added = 0
        elif old_line is not None:
            if raw.startswith("\\ No newline"):
                continue
            if raw.startswith(" "):
                old_line += 1
            elif raw.startswith("-"):
                removed += 1
                changed.append(old_line)
                old_line += 1
            elif raw.startswith("+"):
                added += 1
    if removed != added or not changed:
        return None
    allowed = (ast.Expr, ast.Assign, ast.AnnAssign, ast.AugAssign,
               ast.Return, ast.Raise, ast.Assert, ast.Delete,
               ast.Import, ast.ImportFrom)
    spans = set()
    for line in changed:
        candidates = [node for node in ast.walk(tree) if isinstance(node, ast.stmt)
                      and hasattr(node, "lineno") and node.lineno <= line <= node.end_lineno]
        if not candidates:
            return None
        node = min(candidates, key=lambda n: (n.end_lineno - n.lineno, -n.lineno))
        if not isinstance(node, allowed):
            return None
        spans.add((node.lineno, node.end_lineno))
    return sorted(spans)


def class_literal_edit(source, patched):
    """Recognize a sole change to the literal value of an existing class field.

    Other structural edits, a changed field target, and values with executable
    expressions are deliberately excluded. Containers of pure literal values
    are admitted, including parser tables. This never infers that a change is
    harmless; it only permits using observed class consumers.
    """
    before, after = ast.parse(source, type_comments=True), ast.parse(patched, type_comments=True)

    def fields(tree):
        found = {}

        def walk(body, prefix):
            for node in body:
                if not isinstance(node, ast.ClassDef):
                    continue
                qual = prefix + node.name
                for stmt in node.body:
                    name = None
                    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                        name = stmt.targets[0].id
                    elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        name = stmt.target.id
                    if name:
                        found.setdefault((qual, name), []).append(stmt)
                walk(node.body, qual + ".")

        walk(tree.body, "")
        return found

    old, new = fields(before), fields(after)
    options = []
    for key in old.keys() & new.keys():
        if len(old[key]) != 1 or len(new[key]) != 1:
            continue
        a, b = old[key][0], new[key][0]
        if a.value is None or b.value is None:
            continue
        if ast.dump(a.value, include_attributes=False) == ast.dump(b.value, include_attributes=False):
            continue
        try:
            av, bv = ast.literal_eval(a.value), ast.literal_eval(b.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            continue
        def pure(value):
            if type(value) in (type(None), bool, int, float, str, bytes):
                return True
            if type(value) in (tuple, list, set, frozenset):
                return all(pure(part) for part in value)
            if type(value) is dict:
                return all(pure(k) and pure(v) for k, v in value.items())
            return False

        if not pure(av) or not pure(bv):
            continue
        options.append((key, a, b, av, bv))
    if len(options) != 1:
        return None
    key, a, b, av, bv = options[0]
    a.value = ast.Constant(value="__blast_class_value__")
    b.value = ast.Constant(value="__blast_class_value__")
    if ast.dump(before, include_attributes=False) != ast.dump(after, include_attributes=False):
        return None
    return key, av, bv


class Impact:
    def __init__(self, tests, map_path, mode):
        with gzip.open(map_path, "rt") as handle:
            self.maps = json.load(handle)
        fixture_path = map_path.with_name("fixture-reads.json")
        self.fixture_reads = json.loads(fixture_path.read_text()) if fixture_path.exists() else {}
        shared_path = map_path.with_name("fixture-shared.json")
        self.fixture_shared = json.loads(shared_path.read_text()) if shared_path.exists() else {}
        self.tests = tests
        self.mode = mode
        self.all_ids = {test["id"] for test in tests}
        self.by_file = {}
        self.by_class = {}
        for test in tests:
            self.by_file.setdefault(test["file"], set()).add(test["id"])
            self.by_class.setdefault(test["id"].rsplit("::", 1)[0], set()).add(test["id"])
        self.sources = self.maps["sources"]
        self.static = self.maps["static"]
        self.lines = self.maps.get("lines", {})
        self.contexts = self.maps.get("contexts", [])
        self.readers = self.files_to_ids(self.maps["source_readers"])
        self.subprocess = set(self.maps.get("subprocess", []))
        self.unmapped = self.all_ids.difference(
            test for group in self.contexts for test in group
        )
        class_path = map_path.with_name("class-uses.json.gz")
        with gzip.open(class_path, "rt") if class_path.exists() else open("/dev/null") as handle:
            self.class_uses = json.load(handle) if class_path.exists() else {}
        import_path = map_path.with_name("class-import-reads.json")
        self.class_import_reads = (set(json.loads(import_path.read_text()))
                                   if import_path.exists() else None)
        self.class_unprofiled = self.all_ids - set().union(
            *(set(ids) for ids in self.class_uses.values())) if self.class_uses else set()
        self.reflective_tests = set()
        for path, source in self.sources.items():
            if path.startswith("tests/") and any(token in source for token in
                    ("vars(", "__dict__", "inspect.", "getmembers(", "getattr(")):
                self.reflective_tests.update(self.by_file.get(path, ()))
        self._class_references = {}

    def class_readers(self, name):
        """Use pristine references to include direct class-data readers.

        Module/class-body references can build persistent state during import;
        those require the conservative full-suite fallback.
        """
        if name in self._class_references:
            return self._class_references[name]
        selected = set()
        import_read = False

        def mentions(node):
            return any((isinstance(child, ast.Name) and child.id == name and isinstance(child.ctx, ast.Load))
                       or (isinstance(child, ast.Attribute) and child.attr == name)
                       or (isinstance(child, ast.Constant) and child.value == name)
                       for child in ast.walk(node))

        def direct_mention(node):
            return ((isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Load))
                    or (isinstance(node, ast.Attribute) and node.attr == name)
                    or (isinstance(node, ast.Constant) and node.value == name))

        def scan_body(body):
            nonlocal import_read
            for node in body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    header = [*node.decorator_list, *node.args.defaults, *node.args.kw_defaults]
                    if any(mentions(part) for part in header if part is not None):
                        import_read = True
                    continue
                if isinstance(node, ast.ClassDef):
                    if any(mentions(part) for part in [*node.bases, *node.keywords, *node.decorator_list]):
                        import_read = True
                    scan_body(node.body)
                elif mentions(node):
                    import_read = True

        for path, source in self.sources.items():
            if name not in source:
                continue
            try:
                tree = ast.parse(source)
            except (SyntaxError, RecursionError):
                import_read = True
                continue
            scan_body(tree.body)
            contexts = self.lines.get(path, {})
            for node in ast.walk(tree):
                if not direct_mention(node):
                    continue
                if hasattr(node, "lineno"):
                    index = contexts.get(str(node.lineno))
                    if index is not None:
                        group = set(self.contexts[index])
                        if "" in group:
                            import_read = True
                        selected.update(group)
                if path.startswith("tests/"):
                    selected.update(self.by_file.get(path, ()))
        selected.discard("")
        self._class_references[name] = (selected, import_read)
        return selected, import_read

    def safe_expression_arg_types(self, path, class_name, before, after):
        """Recognize a fixed-key bool schema and its pinned Expr construction hook.

        Expr.__init_subclass__ derives required_args from the schema while the
        class is created. If the keys and value types stay fixed, this hook can
        only change that class's derived required_args, which its users read.
        Other import-time references to this particular schema are excluded.
        """
        if (self.class_import_reads is None or not isinstance(before, dict) or not isinstance(after, dict)
                or before.keys() != after.keys()
                or not all(type(k) is str and type(v) is bool for k, v in before.items())
                or not all(type(v) is bool for v in after.values())):
            return False
        source = self.sources.get(path, "")
        tree = ast.parse(source)
        target = None
        for node in ast.walk(tree):
            if (isinstance(node, ast.ClassDef) and node.name == class_name.rsplit(".", 1)[-1]
                    and any(isinstance(base, ast.Name) and base.id in ("Expr", "Expression")
                            for base in node.bases)):
                target = node
                break
        if target is None:
            return False
        core = ast.parse(self.sources["sqlglot/expressions/core.py"])
        hook = next((member for c in core.body if isinstance(c, ast.ClassDef) and c.name == "Expr"
                     for member in c.body if isinstance(member, ast.FunctionDef)
                     and member.name == "__init_subclass__"), None)
        if hook is None:
            return False
        expected = ("cls.arg_types.items()", "cls.required_args")
        hook_text = ast.unparse(hook)
        if not all(snippet in hook_text for snippet in expected):
            return False
        # The only non-hook read of the derived setting in pinned SQLGlot is
        # Expr.error_messages. Its receiver is captured during every import by
        # the separate clean-suite profile. New or opaque read sites fail closed.
        derived_sites = []
        for source_path, text in self.sources.items():
            if "required_args" not in text:
                continue
            for node in ast.walk(ast.parse(text)):
                if (isinstance(node, ast.Attribute) and node.attr == "required_args"
                        and isinstance(node.ctx, ast.Load)):
                    derived_sites.append((source_path, node.lineno))
        validation = next((member for c in core.body if isinstance(c, ast.ClassDef) and c.name == "Expression"
                           for member in c.body if isinstance(member, ast.FunctionDef)
                           and member.name == "error_messages"), None)
        if validation is None:
            return False
        expected_sites = [("sqlglot/expressions/core.py", node.lineno)
                          for node in ast.walk(validation)
                          if (isinstance(node, ast.Attribute) and node.attr == "required_args"
                              and isinstance(node.ctx, ast.Load))]
        if len(expected_sites) != 1 or derived_sites != expected_sites:
            return False
        # A direct import-time copy of this exact class's schema can produce
        # other classes' derived state; leave it to the broad fallback.
        class_ref = class_name.rsplit(".", 1)[-1] + ".arg_types"
        for other in self.sources.values():
            if class_ref in other:
                return False
        return True

    def files_to_ids(self, files):
        return set().union(*(self.by_file.get(path, set()) for path in files))

    def select_ids(self, patch):
        selected = set()
        try:
            for old, new, hunk in sections(patch):
                if old != new:
                    return self.all_ids
                if any(line.startswith(("deleted file mode", "new file mode",
                                        "rename ", "copy ", "old mode", "new mode",
                                        "--- /dev/null", "+++ /dev/null")) for line in hunk):
                    return self.all_ids
                if readers := self.fixture_reads.get(old):
                    if "" in readers:
                        return self.all_ids
                    selected.update(readers)
                    # Record setup reads separately: expanding every ordinary
                    # per-method fixture read would unnecessarily run a class.
                    for scope in self.fixture_shared.get(old, ()):
                        selected.update(self.by_class.get(scope, self.by_file.get(scope, ())))
                    selected.update(self.subprocess, self.unmapped)
                    continue
                if old not in self.sources:
                    return self.all_ids
                static = self.files_to_ids(self.static.get(old, []))
                if self.mode == "static":
                    if old.startswith("sqlglot/dialects/") or not static:
                        return self.all_ids
                    selected.update(static)
                    continue
                contexts = self.lines.get(old, {})
                if not contexts:
                    return self.all_ids
                spans = None
                if self.mode in {"function", "pool-file", "pool-function", "pool-noop"}:
                    try:
                        source = self.sources[old]
                        patched = apply_hunks(source, hunk)
                        spans = changed_bodies(source, patched)
                        if self.mode.startswith("pool-"):
                            compile(patched, old, "exec", dont_inherit=True)
                    except (ValueError, SyntaxError, RecursionError):
                        spans = None
                if self.mode == "hybrid":
                    # Include static importers even when no baseline execution hit the code.
                    # Lazy imports and fixture paths are covered by observed execution.
                    observed = set().union(*(self.contexts[index] for index in set(contexts.values())))
                    if not static or "" in self.subprocess:
                        return self.all_ids
                    observed.discard("")
                    observed.update(static, self.readers, self.subprocess)
                elif self.mode.startswith("pool-"):
                    if spans == [] and self.mode == "pool-noop" and self.comment_edit(hunk, source, patched):
                        if ast.dump(ast.parse(source, type_comments=True)) != ast.dump(
                            ast.parse(patched, type_comments=True)
                        ):
                            return self.all_ids
                        selected.update(self.readers, self.subprocess, self.unmapped)
                        selected.update(self.by_file.get(old, ()))
                        continue
                    if not spans:
                        if self.class_uses:
                            try:
                                edited_class = class_literal_edit(source, patched)
                            except (ValueError, SyntaxError, RecursionError):
                                edited_class = None
                            if edited_class:
                                (class_name, attr), before, after = edited_class
                                readers, import_read = self.class_readers(attr)
                                expression_schema = (attr == "arg_types" and
                                    self.safe_expression_arg_types(old, class_name, before, after))
                                module = old.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
                                key = module + ":" + class_name
                                if expression_schema and key in self.class_import_reads:
                                    expression_schema = False
                                if expression_schema:
                                    # The reference index includes every Expr's schema.
                                    # Restrict generic read sites to this class's users.
                                    readers = readers & set(self.class_uses.get(key, ()))
                                    derived, _ = self.class_readers("required_args")
                                    readers.update(derived & set(self.class_uses.get(key, ())))
                                    token = class_name.rsplit(".", 1)[-1]
                                    for test_file, test_source in self.sources.items():
                                        if test_file.startswith("tests/") and token in test_source:
                                            readers.update(self.by_file.get(test_file, ()))
                                    readers.update(self.reflective_tests)
                                    import_read = False
                                if not import_read:
                                    users = set(self.class_uses.get(key, ()))
                                    if users:
                                        selected.update(users, readers, self.readers,
                                                        self.subprocess, self.unmapped,
                                                        self.class_unprofiled,
                                                        self.by_file.get(old, ()))
                                        continue
                        if old.startswith("sqlglot/dialects/") and "" not in self.subprocess:
                            observed = set().union(*(self.contexts[index]
                                                     for index in set(contexts.values())))
                            if "" not in observed and observed:
                                selected.update(observed, self.readers, self.subprocess,
                                                self.unmapped, self.by_file.get(old, ()))
                                continue
                        return self.all_ids
                    if self.mode == "pool-file":
                        observed = set().union(*(self.contexts[index]
                                                 for index in set(contexts.values())))
                    else:
                        observed = set()
                        for first, last in spans:
                            context_ids = {index for line, index in contexts.items()
                                           if first <= int(line) <= last}
                            callers = set().union(*(self.contexts[index] for index in context_ids))
                            if not callers or "" in callers:
                                return self.all_ids
                            observed.update(callers)
                        if self.mode == "pool-noop":
                            statements = replacement_statements(source, patched, hunk)
                            if statements and all(any(first <= start <= end <= last
                                                      for first, last in spans)
                                                  for start, end in statements):
                                narrowed = set()
                                for start, end in statements:
                                    context_ids = {index for line, index in contexts.items()
                                                   if start <= int(line) <= end}
                                    readers = set().union(*(self.contexts[index]
                                                            for index in context_ids))
                                    if not readers or "" in readers:
                                        break
                                    narrowed.update(readers)
                                else:
                                    observed = narrowed
                    if not observed:
                        return self.all_ids
                    observed.discard("")
                    observed.update(self.readers, self.subprocess, self.unmapped)
                    observed.update(self.by_file.get(old, ()))
                else:
                    lines = contexts.values() if not spans else (
                        ids for line, ids in contexts.items()
                        if any(first <= int(line) <= last for first, last in spans)
                    )
                    observed = set().union(*(self.contexts[index] for index in set(lines)))
                selected.update(observed)
        except (ValueError, SyntaxError, UnicodeError, RecursionError):
            return self.all_ids
        return selected

    @staticmethod
    def comment_edit(hunk, source, patched):
        signature = re.compile(r"^#!|coding[:=]\s*[-\w.]+")
        old_header = source.splitlines()[:2]
        new_header = patched.splitlines()[:2]
        if old_header != new_header and any(signature.search(line)
                                            for line in old_header + new_header):
            return False
        changed = [line[1:].strip() for line in hunk
                   if line.startswith(("+", "-")) and not line.startswith(("+++ ", "--- "))]
        return bool(changed) and all(not line or line.startswith("#") for line in changed)

    def select(self, patch):
        ids = self.select_ids(patch)
        return [test for test in self.tests if test["id"] in ids]
