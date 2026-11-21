"""Derive test impact from patches and maps of the clean checkout."""
import ast
from functools import lru_cache
import gzip
import hashlib
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
    """Return old statement lines only for adjacent, in-place replacements.

Equal numbers of additions and removals do not establish a replacement:
an inserted early return and a deleted late return can change every call.
    Limit this optimization to a one-line statement replaced immediately by
    another one-line statement of the same kind, or an if header with
    unchanged branches. All other shapes use the
    existing whole-function coverage fallback.
    """
    old_tree, new_tree = ast.parse(source), ast.parse(patched)

    def bindings(tree):
        return sorted((type(node.ctx).__name__, node.id) for node in ast.walk(tree)
                      if isinstance(node, ast.Name)
                      and isinstance(node.ctx, (ast.Store, ast.Del)))

    if bindings(old_tree) != bindings(new_tree):
        return None

    def loads(tree):
        return sorted(node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
                      and isinstance(node.ctx, ast.Load))

    # A new free name such as __class__ can change closure construction even
    # if its statement is never reached by a test.
    if loads(old_tree) != loads(new_tree):
        return None

    allowed = (ast.Expr, ast.Assign, ast.AnnAssign, ast.AugAssign,
               ast.Return, ast.Raise, ast.Assert, ast.Delete,
               ast.Import, ast.ImportFrom)

    def statement(tree, lineno):
        candidates = [node for node in ast.walk(tree) if isinstance(node, ast.stmt)
                      and getattr(node, "lineno", -1) <= lineno <= getattr(node, "end_lineno", -1)]
        if not candidates:
            return None
        node = min(candidates, key=lambda item: (item.end_lineno - item.lineno, -item.lineno))
        if isinstance(node, allowed) and node.lineno == node.end_lineno == lineno:
            return node
        if isinstance(node, ast.If) and node.lineno == lineno:
            return node
        return None

    pairs = []
    removed = []
    added = []
    old_line = new_line = None

    def flush():
        if not removed and not added:
            return True
        if len(removed) != 1 or len(added) != 1:
            return False
        before = statement(old_tree, removed[0])
        after = statement(new_tree, added[0])
        if before is None or after is None or type(before) is not type(after):
            return False
        if isinstance(before, ast.If) and (
                ast.dump(ast.Module(body=before.body, type_ignores=[]))
                != ast.dump(ast.Module(body=after.body, type_ignores=[]))
                or ast.dump(ast.Module(body=before.orelse, type_ignores=[]))
                != ast.dump(ast.Module(body=after.orelse, type_ignores=[]))):
            return False
        if isinstance(before, ast.If):
            # Comprehensions, lambdas, and assignment expressions can change
            # the enclosing function's closure/local layout at compile time
            # even if execution never reaches this header.
            scoped = (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
                      ast.GeneratorExp, ast.NamedExpr, ast.Yield, ast.YieldFrom,
                      ast.Await)
            if any(isinstance(node, scoped) for test in (before.test, after.test)
                   for node in ast.walk(test)):
                return False
        pairs.append((removed[0], removed[0]))
        removed.clear()
        added.clear()
        return True

    for raw in hunk:
        match = HUNK.match(raw) if raw.startswith("@@") else None
        if match:
            if not flush():
                return None
            old_line, new_line = int(match[1]), int(match[3])
            continue
        if old_line is None or raw.startswith("\\ No newline"):
            continue
        if raw.startswith(" "):
            if not flush():
                return None
            old_line += 1
            new_line += 1
        elif raw.startswith("-"):
            if added:
                return None
            removed.append(old_line)
            old_line += 1
        elif raw.startswith("+"):
            if not removed:
                return None
            added.append(new_line)
            new_line += 1
        else:
            return None
    return pairs if flush() and pairs else None


def changed_comment_text(hunk):
    """Keep mixed code/comment edits on the full-suite fallback.

This also catches inline comments and shebangs. A hash inside a string may
occasionally widen the selection, which is safe under the miss penalty.
    """
    return any("#" in raw for raw in hunk if raw.startswith(("+", "-"))
               and not raw.startswith(("+++ ", "--- ")))


def changed_source_header(source, patched):
    """A changed encoding declaration or shebang is observable outside ASTs."""
    old = source.splitlines()[:2]
    new = patched.splitlines()[:2]
    if old == new:
        return False
    signature = re.compile(r"^#!|coding[:=]\s*[-\w.]+")
    return any(signature.search(line) for line in old + new)


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


def class_lambda_edit(source, patched):
    """Find one changed lambda body stored directly in an existing class dict.

    Replacing both bodies by the same sentinel must make the entire module AST
    identical. In particular, this excludes changed dict keys, lambda defaults,
    decorators and any import-time expression around the lambda.
    """
    before, after = ast.parse(source, type_comments=True), ast.parse(patched, type_comments=True)

    def lambdas(tree):
        found = {}

        def classes(body, prefix):
            for node in body:
                if not isinstance(node, ast.ClassDef):
                    continue
                qual = prefix + node.name
                for stmt in node.body:
                    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                            and isinstance(stmt.targets[0], ast.Name)):
                        field, value = stmt.targets[0].id, stmt.value
                    elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        field, value = stmt.target.id, stmt.value
                    else:
                        continue
                    if not isinstance(value, ast.Dict):
                        continue
                    for key, item in zip(value.keys, value.values):
                        if (isinstance(key, ast.Constant) and type(key.value) is str
                                and isinstance(item, ast.Lambda)):
                            found.setdefault((qual, field, key.value), []).append(item)
                classes(node.body, qual + ".")

        classes(tree.body, "")
        return found

    old, new = lambdas(before), lambdas(after)
    choices = []
    for key in old.keys() & new.keys():
        if len(old[key]) != 1 or len(new[key]) != 1:
            continue
        a, b = old[key][0], new[key][0]
        if ast.dump(a.body, include_attributes=False) != ast.dump(b.body, include_attributes=False):
            choices.append((key, a, b))
    if len(choices) != 1:
        return None
    key, a, b = choices[0]
    a.body = ast.Constant(value="__blast_class_lambda_body__")
    b.body = ast.Constant(value="__blast_class_lambda_body__")
    if ast.dump(before, include_attributes=False) != ast.dump(after, include_attributes=False):
        return None
    return key


def class_factory_literal_edit(source, patched):
    """Find one changed literal argument in a class dictionary factory call.

    This recognizes only a pre-existing string key and a direct call to a
    named factory. Every other AST node, including the call target and keyword
    names, must be identical after masking the one changed argument.
    """
    before, after = ast.parse(source, type_comments=True), ast.parse(patched, type_comments=True)

    def calls(tree):
        found = {}

        def classes(body, prefix):
            for node in body:
                if not isinstance(node, ast.ClassDef):
                    continue
                qual = prefix + node.name
                for stmt in node.body:
                    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                            and isinstance(stmt.targets[0], ast.Name)):
                        field, value = stmt.targets[0].id, stmt.value
                    elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        field, value = stmt.target.id, stmt.value
                    else:
                        continue
                    if not isinstance(value, ast.Dict):
                        continue
                    for key, item in zip(value.keys, value.values):
                        if (isinstance(key, ast.Constant) and type(key.value) is str
                                and isinstance(item, ast.Call) and isinstance(item.func, ast.Name)):
                            found.setdefault((qual, field, key.value), []).append(item)
                classes(node.body, qual + ".")

        classes(tree.body, "")
        return found

    old, new = calls(before), calls(after)
    options = []

    def literal(node):
        try:
            value = ast.literal_eval(node)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return False
        return type(value) in (type(None), bool, int, float, str, bytes)

    for key in old.keys() & new.keys():
        if len(old[key]) != 1 or len(new[key]) != 1:
            continue
        a, b = old[key][0], new[key][0]
        if (a.func.id != b.func.id or len(a.args) != len(b.args)
                or len(a.keywords) != len(b.keywords)
                or any(not literal(arg) for arg in a.args + b.args)
                or any(kw.arg is None or not literal(kw.value)
                       for kw in a.keywords + b.keywords)
                or [kw.arg for kw in a.keywords] != [kw.arg for kw in b.keywords]):
            continue
        positions = [(x, y) for x, y in zip(a.args, b.args)]
        positions += [(x.value, y.value) for x, y in zip(a.keywords, b.keywords)]
        changes = [(x, y) for x, y in positions
                   if ast.dump(x, include_attributes=False) != ast.dump(y, include_attributes=False)]
        if len(changes) != 1:
            continue
        options.append((key, a, b, changes[0]))
    if len(options) != 1:
        return None
    key, a, b, (old_arg, new_arg) = options[0]
    for call, target in ((a, old_arg), (b, new_arg)):
        replacement = ast.Constant(value="__blast_factory_literal__")
        for i, arg in enumerate(call.args):
            if arg is target:
                call.args[i] = replacement
        for keyword in call.keywords:
            if keyword.value is target:
                keyword.value = replacement
    if ast.dump(before, include_attributes=False) != ast.dump(after, include_attributes=False):
        return None
    return key, a.func.id


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
        try:
            with gzip.open(class_path, "rt") as handle:
                parent_classes = json.load(handle)
            self.parent_class_map_valid = (
                isinstance(parent_classes, dict)
                and all(type(key) is str and isinstance(ids, list)
                        and ids == sorted(set(ids)) and set(ids) <= self.all_ids
                        for key, ids in parent_classes.items()))
        except (OSError, ValueError, TypeError):
            parent_classes = {}
            self.parent_class_map_valid = False
        self.class_uses = ({key: set(ids) for key, ids in parent_classes.items()}
                           if self.parent_class_map_valid else {})
        import_path = map_path.with_name("class-import-reads.json")
        self.class_import_reads = (set(json.loads(import_path.read_text()))
                                   if import_path.exists() else None)
        constructor_path = map_path.with_name("class-import-constructors.json")
        self.class_import_constructors = (set(json.loads(constructor_path.read_text()))
                                          if constructor_path.exists() else None)
        lambda_path = map_path.with_name("parser-lambda-import-calls.json")
        try:
            payload = json.loads(lambda_path.read_text())
            if (not isinstance(payload, dict)
                    or payload.get("impact_sha256")
                    != hashlib.sha256(map_path.read_bytes()).hexdigest()):
                raise ValueError("lambda import map does not match impact map")
            lambda_calls = payload.get("calls")
            shared_calls = payload.get("shared_calls")
            if not isinstance(lambda_calls, list) or not isinstance(shared_calls, list) or not all(
                    isinstance(row, list) and len(row) == 3
                    and type(row[0]) is str and type(row[1]) is int
                    and type(row[2]) is str for row in lambda_calls + shared_calls):
                raise ValueError("invalid lambda import call map")
            self.parser_lambda_import_calls = {(path, line) for path, line, _
                                               in lambda_calls + shared_calls}
        except (OSError, ValueError, TypeError):
            self.parser_lambda_import_calls = None
        pool_path = map_path.with_name("pool-classes.json.gz")
        try:
            with gzip.open(pool_path, "rt") as handle:
                pool = json.load(handle)
        except (OSError, ValueError):
            pool = None
        self.pool_classes = pool if self.valid_pool_classes(pool) else None
        if self.pool_classes is not None:
            for key, ids in pool["classes"].items():
                self.class_uses.setdefault(key, set()).update(ids)
            self.subprocess.update(pool["nested"])
        numeric_path = map_path.with_name("numeric-key-uses.json.gz")
        try:
            with gzip.open(numeric_path, "rt") as handle:
                numeric = json.load(handle)
        except (OSError, ValueError):
            numeric = None
        self.numeric_key_uses = (numeric if self.valid_numeric_key_uses(numeric, map_path)
                                 else None)
        self.class_unprofiled = self.all_ids - set().union(
            *(set(ids) for ids in self.class_uses.values())) if self.class_uses else set()
        self.reflective_tests = set()
        for path, source in self.sources.items():
            if path.startswith("tests/") and any(token in source for token in
                    ("vars(", "__dict__", "inspect.", "getmembers(", "getattr(")):
                self.reflective_tests.update(self.by_file.get(path, ()))
        self._class_references = {}
        reference_path = map_path.with_name("reference-index.json.gz")
        self.reference_index = {}
        try:
            with gzip.open(reference_path, "rt") as handle:
                reference = json.load(handle)
            if (isinstance(reference, dict)
                    and reference.get("impact_sha256") == hashlib.sha256(map_path.read_bytes()).hexdigest()
                    and isinstance(reference.get("references"), dict)):
                self.reference_index = reference["references"]
        except (OSError, ValueError, TypeError):
            pass

    def valid_pool_classes(self, pool):
        """Reject an incomplete or stale child map before using class fast paths."""
        if (not isinstance(pool, dict) or set(pool) != {
                "classes", "callers", "caller_tasks", "nested", "tasks"}):
            return False
        classes, callers, counts = pool["classes"], pool["callers"], pool["caller_tasks"]
        nested, tasks = pool["nested"], pool["tasks"]
        if (not isinstance(classes, dict) or not isinstance(callers, list)
                or not isinstance(counts, dict) or not isinstance(nested, list)
                or type(tasks) is not int or tasks <= 0
                or any(type(x) is not str for x in callers)
                or callers != sorted(set(callers)) or not set(callers) <= self.all_ids
                or set(counts) != set(callers)
                or any(type(v) is not int or v <= 0 for v in counts.values())
                or sum(counts.values()) != tasks
                or any(type(x) is not str for x in nested)
                or nested != sorted(set(nested)) or not set(nested) <= set(callers)):
            return False
        pool_files = {path for path, source in self.sources.items()
                      if path.startswith("tests/") and "ProcessPoolExecutor" in source}
        if {nodeid.split("::", 1)[0] for nodeid in callers} != pool_files:
            return False
        return all(type(key) is str and key.startswith("sqlglot.")
                   and isinstance(ids, list)
                   and all(type(nodeid) is str for nodeid in ids)
                   and ids == sorted(set(ids))
                   and set(ids) <= set(callers) for key, ids in classes.items())

    def valid_numeric_key_uses(self, numeric, map_path):
        """Require a complete, pristine-key trace before using per-key reads."""
        if (self.pool_classes is None or not isinstance(numeric, dict)
                or set(numeric) != {"uses", "import_reads", "nested", "callers",
                                    "caller_tasks", "tasks", "impact_sha256"}
                or numeric["impact_sha256"] != hashlib.sha256(map_path.read_bytes()).hexdigest()
                or any(numeric[name] != self.pool_classes[name] for name in
                       ("callers", "caller_tasks", "tasks", "nested"))
                or not isinstance(numeric["uses"], dict)
                or not isinstance(numeric["import_reads"], dict)):
            return False
        for owner, keys in numeric["uses"].items():
            if type(owner) is not str or not owner.startswith("sqlglot.") or not isinstance(keys, dict):
                return False
            for key, ids in keys.items():
                if (type(key) is not str or len(key) != 1 or not isinstance(ids, list)
                        or any(type(nodeid) is not str for nodeid in ids)
                        or ids != sorted(set(ids)) or not set(ids) <= self.all_ids):
                    return False
        for owner, keys in numeric["import_reads"].items():
            if (owner not in numeric["uses"] or not isinstance(keys, list)
                    or any(type(key) is not str for key in keys)
                    or keys != sorted(set(keys))
                    or not set(keys) <= set(numeric["uses"][owner])):
                return False
        return True

    def class_readers(self, name):
        """Use pristine references to include direct class-data readers.

        Module/class-body references can build persistent state during import;
        those require the conservative full-suite fallback.
        """
        if name in self._class_references:
            return self._class_references[name]
        entry = self.reference_index.get(name)
        if (isinstance(entry, list) and len(entry) == 3
                and isinstance(entry[0], list) and all(isinstance(value, str) for value in entry[0])
                and isinstance(entry[1], list) and all(isinstance(value, str) for value in entry[1])
                and isinstance(entry[2], bool)):
            selected = set(entry[0]) | self.files_to_ids(entry[1])
            self._class_references[name] = (selected, bool(entry[2]))
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

    def factory_readers(self, path, class_name, field):
        """Exclude a foreign class's proven local trie-key read of its own table.

        This is used only after safe_parser_closure_factory has proved that a
        value-only factory edit cannot change the target class's derived trie.
        A bare name in another class body resolves to that class's preceding
        assignment, so its read cannot consume the edited subclass table.
        Every other reference retains the ordinary class-reader selection.
        """
        selected = set()
        for source_path, text in self.sources.items():
            if field not in text:
                continue
            try:
                tree = ast.parse(text)
            except (SyntaxError, RecursionError):
                return self.all_ids
            excluded = set()
            trie_imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)
                            and node.module == "sqlglot.trie"
                            for alias in node.names
                            if alias.name == "new_trie" and alias.asname is None]
            trie_rebound = any(
                isinstance(node, ast.Name) and node.id == "new_trie"
                and isinstance(node.ctx, (ast.Store, ast.Del)) for node in ast.walk(tree)
            ) or any(
                (alias.asname or alias.name) == "new_trie"
                and not (isinstance(node, ast.ImportFrom)
                         and node.module == "sqlglot.trie"
                         and alias.name == "new_trie" and alias.asname is None)
                for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names
            )
            for owner in (node for node in tree.body if isinstance(node, ast.ClassDef)):
                if ((source_path, owner.name) == (path, class_name)
                        or owner.decorator_list or owner.keywords or trie_rebound
                        or len(trie_imports) != 1):
                    continue
                fields = [stmt for stmt in owner.body if isinstance(stmt, ast.Assign)
                          and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)
                          and stmt.targets[0].id == field]
                if (len(fields) != 1 or not isinstance(fields[0].value, ast.Dict)
                        or not all(isinstance(key, ast.Constant) and isinstance(key.value, str)
                                   for key in fields[0].value.keys)
                        or [node for node in ast.walk(owner)
                        if isinstance(node, ast.Name) and node.id == field
                        and isinstance(node.ctx, (ast.Store, ast.Del))] != fields[0].targets):
                    continue
                has_local_field = False
                for stmt in owner.body:
                    if (has_local_field and isinstance(stmt, ast.Assign)
                            and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)
                            and stmt.targets[0].id == "SHOW_TRIE"
                            and isinstance(stmt.value, ast.Call)
                            and isinstance(stmt.value.func, ast.Name)
                            and stmt.value.func.id == "new_trie"
                            and len(stmt.value.args) == 1 and not stmt.value.keywords
                            and isinstance(stmt.value.args[0], ast.GeneratorExp)
                            and len(stmt.value.args[0].generators) == 1):
                        generator = stmt.value.args[0]
                        loop = generator.generators[0]
                        if (not loop.ifs and not loop.is_async
                                and isinstance(loop.iter, ast.Name) and loop.iter.id == field
                                and isinstance(loop.target, ast.Name)
                                and isinstance(generator.elt, ast.Call)
                                and isinstance(generator.elt.func, ast.Attribute)
                                and isinstance(generator.elt.func.value, ast.Name)
                                and generator.elt.func.value.id == loop.target.id
                                and generator.elt.func.attr == "split"
                                and len(generator.elt.args) == 1
                                and isinstance(generator.elt.args[0], ast.Constant)
                                and generator.elt.args[0].value == " "
                                and not generator.elt.keywords):
                            excluded.add(loop.iter)
                    if stmt is fields[0]:
                        has_local_field = True
            contexts = self.lines.get(source_path, {})
            for node in ast.walk(tree):
                if node in excluded:
                    continue
                if not ((isinstance(node, ast.Name) and node.id == field
                         and isinstance(node.ctx, ast.Load))
                        or (isinstance(node, ast.Attribute) and node.attr == field)
                        or (isinstance(node, ast.Constant) and node.value == field)):
                    continue
                if hasattr(node, "lineno"):
                    index = contexts.get(str(node.lineno))
                    if index is not None:
                        selected.update(self.contexts[index])
                if source_path.startswith("tests/"):
                    selected.update(self.by_file.get(source_path, ()))
        selected.discard("")
        return selected

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

    def safe_parser_dispatch_lambda(self, path, class_name, field):
        """Admit one runtime parser dispatch body after proving its class shape.

        Python creates a lambda object in the class body but does not execute
        that body's expressions. Parser has no class construction hook, and
        the pristine suite's import phase did not instantiate this receiver.
        An exact reference to its table elsewhere may copy/call the function
        without a Parser receiver, so leave those edits to the broad path.
        """
        if (field != "FUNCTIONS" or not path.startswith("sqlglot/parsers/")
                or self.class_import_constructors is None):
            return False
        module = path.removesuffix(".py").replace("/", ".")
        key = module + ":" + class_name
        if key in self.class_import_constructors or key not in self.class_uses:
            return False
        source = ast.parse(self.sources[path])
        owners = [node for node in source.body if isinstance(node, ast.ClassDef)
                  and node.name == class_name]
        if len(owners) != 1:
            return False
        owner = owners[0]
        if (owner.decorator_list or owner.keywords or len(owner.bases) != 1
                or not isinstance(owner.bases[0], ast.Attribute)
                or not isinstance(owner.bases[0].value, ast.Name)
                or (owner.bases[0].value.id, owner.bases[0].attr) != ("parser", "Parser")
                or any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and node.name in {"__init__", "__new__"} for node in owner.body)):
            return False
        parser = ast.parse(self.sources["sqlglot/parser.py"])
        roots = [node for node in parser.body if isinstance(node, ast.ClassDef)
                 and node.name == "Parser"]
        if (len(roots) != 1 or roots[0].bases or roots[0].keywords
                or roots[0].decorator_list or any(
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "__init_subclass__" for node in roots[0].body)):
            return False
        # Exclude direct table aliases and calls outside the target class.
        # The dialect's class binding (Parser = DremioParser) is still safe:
        # runtime uses of that class are captured by constructor profiling.
        direct = class_name + "." + field
        if any(direct in text for text in self.sources.values()):
            return False
        return True

    def parser_lambda_readers(self, path, class_name, field, entry):
        """Keep dynamic table readers and observed calls of the edited lambda.

        A class-body copy from a statically different Parser base cannot copy
        this subclass's table. Parser's own `self.FUNCTIONS` read is covered by
        the exact receiver constructor map; all other runtime table readers
        and the lambda body's observed executions stay selected.
        """
        if self.parser_lambda_import_calls is None:
            return None
        target_module = path.removesuffix(".py").replace("/", ".")
        tree = ast.parse(self.sources[path])
        owners = [n for n in tree.body if isinstance(n, ast.ClassDef)
                  and n.name == class_name]
        if len(owners) != 1:
            return None
        fields = [n for n in owners[0].body if isinstance(n, ast.Assign)
                  and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                  and n.targets[0].id == field and isinstance(n.value, ast.Dict)]
        if len(fields) != 1:
            return None
        lambdas = [v for k, v in zip(fields[0].value.keys, fields[0].value.values)
                   if isinstance(k, ast.Constant) and k.value == entry
                   and isinstance(v, ast.Lambda)]
        if len(lambdas) != 1:
            return None
        target = lambdas[0]
        if (path, target.lineno) in self.parser_lambda_import_calls:
            return None
        selected = set()
        passive_factories = {}

        def passive_factory(source_path, source_tree, name):
            cache_key = (source_path, name)
            if cache_key in passive_factories:
                return passive_factories[cache_key]
            functions = [n for n in source_tree.body if isinstance(n, ast.FunctionDef)
                         and n.name == name]
            definition = source_tree
            if not functions:
                imports = [n for n in source_tree.body if isinstance(n, ast.ImportFrom)
                           and n.module and n.module.startswith("sqlglot.")
                           for alias in n.names if (alias.asname or alias.name) == name]
                if len(imports) == 1:
                    factory_path = imports[0].module.replace(".", "/") + ".py"
                    if factory_path in self.sources:
                        definition = ast.parse(self.sources[factory_path])
                        functions = [n for n in definition.body
                                     if isinstance(n, ast.FunctionDef) and n.name == name]
            result = False
            if len(functions) == 1 and not functions[0].decorator_list:
                body = functions[0].body
                result = (len(body) == 2 and isinstance(body[0], ast.FunctionDef)
                          and isinstance(body[1], ast.Return)
                          and isinstance(body[1].value, ast.Name)
                          and body[1].value.id == body[0].name
                          and not body[0].decorator_list
                          and not body[0].args.defaults
                          and not any(v is not None for v in body[0].args.kw_defaults)
                          and any(isinstance(n, ast.ImportFrom)
                                  and n.module == "__future__"
                                  and any(alias.name == "annotations" for alias in n.names)
                                  for n in definition.body))
            passive_factories[cache_key] = result
            return result

        target_lines = self.lines.get(path, {})
        if not target_lines:
            return None
        for line in range(target.body.lineno, target.body.end_lineno + 1):
            index = target_lines.get(str(line))
            if index is None:
                continue
            group = set(self.contexts[index])
            # A same-line class definition is traced during import, too. The
            # class/alias audit below rules out import-time invocation via an
            # unconstructed receiver. A later body line with an import hit is
            # an actual import-time call and requires the broad fallback.
            if "" in group and line != target.lineno:
                return None
            group.discard("")
            selected.update(group)

        for source_path, text in self.sources.items():
            if field not in text:
                continue
            root = tree if source_path == path else ast.parse(text)
            parents = {child: node for node in ast.walk(root)
                       for child in ast.iter_child_nodes(node)}
            aliases = {class_name}
            for imp in root.body:
                if isinstance(imp, ast.ImportFrom) and imp.module == target_module:
                    aliases.update((alias.asname or alias.name) for alias in imp.names
                                   if alias.name == class_name)
            for candidate in ast.walk(root):
                if not isinstance(candidate, ast.ClassDef):
                    continue
                if any((isinstance(base, ast.Name) and base.id in aliases)
                       or (isinstance(base, ast.Attribute) and base.attr == class_name)
                       for base in candidate.bases):
                    return None

            def enclosing(node):
                child = node
                while child in parents:
                    child = parents[child]
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                          ast.Lambda, ast.ClassDef)):
                        return child
                return None

            def is_read(node):
                return ((isinstance(node, ast.Name) and node.id == field
                         and isinstance(node.ctx, ast.Load))
                        or (isinstance(node, ast.Attribute) and node.attr == field
                            and isinstance(node.ctx, ast.Load))
                        or (isinstance(node, ast.Constant) and node.value == field))

            for node in ast.walk(root):
                if not is_read(node):
                    continue
                if source_path.startswith("tests/"):
                    scope = node
                    runtime_scope = False
                    while scope in parents:
                        child = scope
                        scope = parents[scope]
                        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef,
                                              ast.Lambda)):
                            runtime_scope = (isinstance(scope, ast.Lambda)
                                             and child is scope.body) or (
                                                 hasattr(scope, "body")
                                                 and isinstance(scope.body, list)
                                                 and child in scope.body)
                            break
                    if not runtime_scope:
                        # A collection-time test-module read can seed state
                        # observed by tests in another file.
                        return None
                    selected.update(self.by_file.get(source_path, ()))
                    continue
                if isinstance(node, ast.Constant) and isinstance(parents.get(node), ast.Dict):
                    if node in parents[node].keys:
                        continue
                ancestor = enclosing(node)
                if isinstance(ancestor, ast.ClassDef):
                    if ancestor.name == class_name and source_path == path:
                        # An unexpected import-time read of the edited table
                        # could construct persistent state for other tests.
                        if node not in ast.walk(fields[0]):
                            return None
                        continue
                    if isinstance(node, ast.Constant) and ancestor.name != class_name:
                        call = parents.get(node)
                        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                                and passive_factory(source_path, root, call.func.id)):
                            # A passive factory merely captures this string
                            # for a different class's runtime dispatch.
                            continue
                        # getattr(alias, "FUNCTIONS") and other active calls
                        # can copy our changed table during import.
                        return None
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                        receiver = node.value.id
                        bases = {base.id for base in ancestor.bases if isinstance(base, ast.Name)}
                        if receiver in bases and receiver not in aliases:
                            continue
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute):
                        receiver = node.value
                        if (receiver.attr == "Parser" and isinstance(receiver.value, ast.Name)
                                and receiver.value.id == "parser"):
                            continue
                    if isinstance(node, ast.Name) and ancestor.name != class_name:
                        continue
                    return None
                if (source_path == "sqlglot/parser.py" and isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name) and node.value.id == "self"
                        and isinstance(ancestor, ast.FunctionDef)
                        and ancestor.args.args and ancestor.args.args[0].arg == "self"
                        and isinstance(parents.get(ancestor), ast.ClassDef)
                        and parents[ancestor].name == "Parser"):
                    continue
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    if node.value.id in aliases:
                        return None
                index = self.lines.get(source_path, {}).get(str(node.lineno))
                if index is None:
                    return None
                group = set(self.contexts[index])
                if "" in group:
                    return None
                selected.update(group)
        return selected

    def safe_parser_closure_factory(self, path, class_name, field, factory):
        """Prove that a class table factory only captures literal arguments.

        A factory call made while the class body runs must have no observable
        work until its returned closure is called on a Parser. The pinned
        class cannot have a construction hook inspecting its table values.
        """
        if (field != "SHOW_PARSERS" or not path.startswith("sqlglot/parsers/")
                or self.class_import_constructors is None):
            return False
        module = path.removesuffix(".py").replace("/", ".")
        key = module + ":" + class_name
        if key in self.class_import_constructors or key not in self.class_uses:
            return False
        if any(class_name + "." + field in text for text in self.sources.values()):
            # A derived class may import-copy the table and later call the
            # changed closure without constructing the original class.
            return False

        def find_class(source_path, name):
            tree = ast.parse(self.sources[source_path])
            classes = [node for node in tree.body if isinstance(node, ast.ClassDef)
                       and node.name == name]
            return (tree, classes[0]) if len(classes) == 1 else (tree, None)

        source, owner = find_class(path, class_name)
        if owner is None:
            return False
        # Follow simple import-from class inheritance through the pristine
        # parser package; any decorators, metaclasses or hooks fail closed.
        current_path, current_tree, current = path, source, owner
        for _ in range(8):
            if (current.decorator_list or current.keywords or len(current.bases) != 1
                    or any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                           and n.name in {"__init_subclass__", "__init__", "__new__"}
                           for n in current.body)):
                return False
            base = current.bases[0]
            if (isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name)
                    and (base.value.id, base.attr) == ("parser", "Parser")):
                break
            if not isinstance(base, ast.Name):
                return False
            imports = [n for n in current_tree.body if isinstance(n, ast.ImportFrom)
                       and n.module and n.module.startswith("sqlglot.parsers.")
                       for alias in n.names if (alias.asname or alias.name) == base.id]
            if len(imports) != 1:
                return False
            current_path = imports[0].module.replace(".", "/") + ".py"
            if current_path not in self.sources:
                return False
            current_tree, current = find_class(current_path, base.id)
            if current is None:
                return False
        else:
            return False
        parser = ast.parse(self.sources["sqlglot/parser.py"])
        roots = [n for n in parser.body if isinstance(n, ast.ClassDef) and n.name == "Parser"]
        if (len(roots) != 1 or roots[0].bases or roots[0].keywords
                or roots[0].decorator_list or any(
                    isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name == "__init_subclass__" for n in roots[0].body)):
            return False

        fields = [n for n in owner.body if isinstance(n, ast.Assign)
                  and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                  and n.targets[0].id == field]
        if len(fields) != 1:
            return False
        trie_imports = [n for n in source.body if isinstance(n, ast.ImportFrom)
                        and n.module == "sqlglot.trie"
                        for alias in n.names if alias.name == "new_trie" and alias.asname is None]
        if (len(trie_imports) != 1 or any(
                isinstance(n, ast.Name) and n.id == "new_trie"
                and isinstance(n.ctx, (ast.Store, ast.Del)) for n in ast.walk(source))):
            return False
        for stmt in owner.body:
            if stmt is fields[0]:
                continue
            if not any((isinstance(n, ast.Name) and n.id == field
                        and isinstance(n.ctx, ast.Load))
                       or (isinstance(n, ast.Attribute) and n.attr == field)
                       or (isinstance(n, ast.Constant) and n.value == field)
                       for n in ast.walk(stmt)):
                continue
            # A derived trie can depend on the table's keys, but not its
            # changed closure or values.
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id == "SHOW_TRIE"
                    and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Name)
                    and stmt.value.func.id == "new_trie"
                    and len(stmt.value.args) == 1
                    and not stmt.value.keywords
                    and isinstance(stmt.value.args[0], ast.GeneratorExp)
                    and len(stmt.value.args[0].generators) == 1
                    and not stmt.value.args[0].generators[0].ifs
                    and not stmt.value.args[0].generators[0].is_async
                    and isinstance(stmt.value.args[0].generators[0].iter, ast.Name)
                    and stmt.value.args[0].generators[0].iter.id == field
                    and isinstance(stmt.value.args[0].generators[0].target, ast.Name)
                    and isinstance(stmt.value.args[0].elt, ast.Call)
                    and isinstance(stmt.value.args[0].elt.func, ast.Attribute)
                    and isinstance(stmt.value.args[0].elt.func.value, ast.Name)
                    and stmt.value.args[0].elt.func.value.id
                    == stmt.value.args[0].generators[0].target.id
                    and stmt.value.args[0].elt.func.attr == "split"
                    and len(stmt.value.args[0].elt.args) == 1
                    and isinstance(stmt.value.args[0].elt.args[0], ast.Constant)
                    and stmt.value.args[0].elt.args[0].value == " "
                    and not stmt.value.args[0].elt.keywords
                    and [n for n in ast.walk(stmt) if isinstance(n, ast.Name)
                         and n.id == field and isinstance(n.ctx, ast.Load)]
                    == [stmt.value.args[0].generators[0].iter]):
                return False

        # A different alias such as Dialect.Parser.SHOW_PARSERS could copy or
        # call this table during import without constructing its owning class.
        # The only SQLGlot attribute reads allowed are the base class table
        # merged into this table and Parser's runtime instance dispatch.
        owner_base = owner.bases[0].id if isinstance(owner.bases[0], ast.Name) else None
        for source_path, text in self.sources.items():
            if not source_path.startswith("sqlglot/") or field not in text:
                continue
            for node in ast.walk(source if source_path == path else ast.parse(text)):
                if not (isinstance(node, ast.Attribute) and node.attr == field
                        and isinstance(node.ctx, ast.Load)):
                    continue
                base_copy = (source_path == path and isinstance(node.value, ast.Name)
                             and node.value.id == owner_base
                             and any(node in ast.walk(field_node) for field_node in fields))
                runtime_read = (source_path == "sqlglot/parser.py"
                                and isinstance(node.value, ast.Name)
                                and node.value.id == "self")
                if not (base_copy or runtime_read):
                    return False

        imports = [n for n in source.body if isinstance(n, ast.ImportFrom)
                   and n.module and n.module.startswith("sqlglot.")
                   for alias in n.names if (alias.asname or alias.name) == factory]
        if len(imports) != 1:
            return False
        factory_path = imports[0].module.replace(".", "/") + ".py"
        if factory_path not in self.sources:
            return False
        factory_source = ast.parse(self.sources[factory_path])
        functions = [n for n in factory_source.body if isinstance(n, ast.FunctionDef)
                     and n.name == factory]
        if (len(functions) != 1 or functions[0].decorator_list
                or getattr(functions[0], "type_params", ())):
            return False
        body = functions[0].body
        if (len(body) != 2 or not isinstance(body[0], ast.FunctionDef)
                or not isinstance(body[1], ast.Return)
                or not isinstance(body[1].value, ast.Name)
                or body[1].value.id != body[0].name
                or body[0].decorator_list or body[0].args.defaults
                or getattr(body[0], "type_params", ())
                or any(arg is not None for arg in body[0].args.kw_defaults)):
            return False
        has_future_annotations = any(
            isinstance(n, ast.ImportFrom) and n.module == "__future__"
            and any(alias.name == "annotations" for alias in n.names)
            for n in factory_source.body)
        annotations = [arg.annotation for arg in (
            *body[0].args.posonlyargs, *body[0].args.args, *body[0].args.kwonlyargs)
            if arg.annotation is not None]
        annotations += [arg.annotation for arg in (body[0].args.vararg, body[0].args.kwarg)
                        if arg is not None and arg.annotation is not None]
        if body[0].returns is not None:
            annotations.append(body[0].returns)
        if annotations and not has_future_annotations:
            return False
        return True

    def safe_numeric_escape_values(self, path, class_name, before, after):
        """Narrow fixed-key numeric escape edits after verifying import behavior.

        The pinned dialect metaclass examines only the keys while constructing
        derived escape tables. Values flow to runtime Tokenizer instances. This
        condition fails closed if that metaclass or any SQLGlot read site changes.
        """
        if (self.class_import_constructors is None or self.pool_classes is None
                or not path.startswith("sqlglot/dialects/")
                or not class_name.endswith(".Tokenizer") or not isinstance(before, dict)
                or not isinstance(after, dict) or before.keys() != after.keys()
                or not all(type(k) is str and type(v) is tuple and len(v) == 4
                           and all(type(x) is int for x in v) for k, v in before.items())
                or not all(type(v) is tuple and len(v) == 4
                           and all(type(x) is int for x in v) for v in after.values())):
            return False
        module = path.removesuffix(".py").replace("/", ".")
        token_key = module + ":" + class_name
        parent_key = module + ":" + class_name.removesuffix(".Tokenizer")
        if (token_key not in self.class_uses or parent_key not in self.class_uses
                or token_key in self.class_import_constructors
                or parent_key in self.class_import_constructors):
            return False
        source = ast.parse(self.sources[path])
        parent_name = class_name.removesuffix(".Tokenizer")
        parents = [node for node in source.body if isinstance(node, ast.ClassDef)
                   and node.name == parent_name]
        if (len(parents) != 1 or len(parents[0].bases) != 1
                or parents[0].decorator_list or parents[0].keywords) or not (
                isinstance(parents[0].bases[0], ast.Name)
                and parents[0].bases[0].id == "Dialect"):
            return False
        tokens = [node for node in parents[0].body if isinstance(node, ast.ClassDef)
                  and node.name == "Tokenizer"]
        if (len(tokens) != 1 or len(tokens[0].bases) != 1
                or not isinstance(tokens[0].bases[0], ast.Attribute)
                or not isinstance(tokens[0].bases[0].value, ast.Name)
                or (tokens[0].bases[0].value.id, tokens[0].bases[0].attr)
                != ("tokens", "Tokenizer") or tokens[0].decorator_list
                or tokens[0].keywords or any(
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name in {"__init__", "__new__", "_init_core", "tokenize", "tokenizer"}
                    for node in (*parents[0].body, *tokens[0].body))):
            return False
        core_reads = {}
        for source_path, text in self.sources.items():
            if not source_path.startswith("sqlglot/") or "NUMERIC_ESCAPES" not in text:
                continue
            tree = ast.parse(text)
            reads = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                     and n.attr == "NUMERIC_ESCAPES" and isinstance(n.ctx, ast.Load)]
            if reads:
                core_reads[source_path] = len(reads)
        if core_reads != {"sqlglot/dialects/dialect.py": 1,
                          "sqlglot/generator.py": 2,
                          "sqlglot/tokens.py": 1}:
            return False
        generator = ast.parse(self.sources["sqlglot/generator.py"])
        ancestors = {child: node for node in ast.walk(generator)
                     for child in ast.iter_child_nodes(node)}
        generator_reads = [node for node in ast.walk(generator)
                           if isinstance(node, ast.Attribute)
                           and node.attr == "NUMERIC_ESCAPES" and isinstance(node.ctx, ast.Load)]
        # A generator only tests whether the table is nonempty or contains
        # the fixed 'x' key; a value-only edit cannot change either condition.
        read_uses = [ancestors[node] for node in generator_reads]
        if (len(read_uses) != 2 or not any(
                isinstance(use, ast.BoolOp) and isinstance(use.op, ast.Or)
                and use.values[0] is generator_reads[i]
                for i, use in enumerate(read_uses)) or not any(
                    isinstance(use, ast.Compare) and len(use.ops) == 1
                    and isinstance(use.ops[0], ast.In)
                    and isinstance(use.left, ast.Constant) and use.left.value == "x"
                    and use.comparators == [generator_reads[i]]
                    for i, use in enumerate(read_uses))):
            return False
        dialect = ast.parse(self.sources["sqlglot/dialects/dialect.py"])
        meta = next((n for n in dialect.body if isinstance(n, ast.ClassDef)
                     and n.name == "_Dialect"), None)
        method = next((n for n in meta.body if isinstance(n, ast.FunctionDef)
                       and n.name == "__new__"), None) if meta else None
        if method is None:
            return False
        assignments = [n for n in ast.walk(method) if isinstance(n, ast.Assign)
                       and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                       and n.targets[0].id == "numeric_escapes"]
        if (len(assignments) != 1 or not isinstance(assignments[0].value, ast.Attribute)
                or assignments[0].value.attr != "NUMERIC_ESCAPES"):
            return False
        references = [n for n in ast.walk(method) if isinstance(n, ast.Name)
                      and n.id == "numeric_escapes" and isinstance(n.ctx, ast.Load)]
        comparisons = [n for n in ast.walk(method) if isinstance(n, ast.Compare)
                       and len(n.ops) == 1 and isinstance(n.ops[0], ast.In)
                       and isinstance(n.left, ast.Constant) and type(n.left.value) is str
                       and len(n.comparators) == 1 and isinstance(n.comparators[0], ast.Name)
                       and n.comparators[0].id == "numeric_escapes"]
        if len(references) != 3 or len(comparisons) != 3 or {
                n.left.value for n in comparisons} != {"x", "0", "u"}:
            return False
        hook = ast.parse(self.sources["sqlglot/tokens.py"])
        base = next((n for n in hook.body if isinstance(n, ast.ClassDef)
                     and n.name == "_TokenizerBase"), None)
        subclass = next((n for n in base.body if isinstance(n, ast.FunctionDef)
                         and n.name == "__init_subclass__"), None) if base else None
        if subclass is None or "NUMERIC_ESCAPES" in ast.unparse(subclass):
            return False
        return True

    def numeric_key_data_flow(self):
        """Prove the pinned core consumes tuple data only via keyed lookups.

        The remaining read merely checks whether the fixed-key mapping is
        nonempty. A value-only edit cannot change that condition.
        """
        if not self.numeric_pool_inputs_safe():
            return False
        for path, source in self.sources.items():
            if (not path.startswith("sqlglot/")
                    or ("numeric_escapes" not in source and "_init_core" not in source)):
                continue
            tree = ast.parse(source)
            if path.startswith("sqlglot/dialects/") and any(
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "_init_core" for node in ast.walk(tree)):
                return False
            if path != "sqlglot/tokenizer_core.py" and any(
                    isinstance(node, ast.Attribute) and node.attr == "numeric_escapes"
                    and isinstance(node.ctx, ast.Load) for node in ast.walk(tree)):
                return False
        tree = ast.parse(self.sources["sqlglot/tokenizer_core.py"])
        all_accesses = [node for node in ast.walk(tree) if isinstance(node, ast.Attribute)
                        and node.attr == "numeric_escapes"]
        if len(all_accesses) != 4 or sum(isinstance(node.ctx, ast.Load)
                                         for node in all_accesses) != 3:
            return False
        core = next((node for node in tree.body if isinstance(node, ast.ClassDef)
                     and node.name == "TokenizerCore"), None)
        if core is None:
            return False
        accesses = {}
        for method in core.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            hits = [node for node in ast.walk(method) if isinstance(node, ast.Attribute)
                    and node.attr == "numeric_escapes"]
            if hits:
                accesses[method.name] = hits
        if (set(accesses) != {"__init__", "_read_byte_escape",
                             "_scan_numeric_escape", "_extract_string"}
                or any(len(hits) != 1 for hits in accesses.values())
                or not isinstance(accesses["__init__"][0].ctx, ast.Store)
                or any(not isinstance(accesses[name][0].ctx, ast.Load)
                       for name in ("_read_byte_escape", "_scan_numeric_escape", "_extract_string"))):
            return False
        init = next(node for node in core.body if isinstance(node, ast.FunctionDef)
                    and node.name == "__init__")
        init_reads = [node for node in ast.walk(init) if isinstance(node, ast.Name)
                      and node.id == "numeric_escapes" and isinstance(node.ctx, ast.Load)]
        init_assignments = [node for node in ast.walk(init) if isinstance(node, ast.Assign)
                            and len(node.targets) == 1
                            and node.targets[0] is accesses["__init__"][0]
                            and node.value in init_reads]
        if len(init_reads) != 1 or len(init_assignments) != 1:
            return False
        tokens = ast.parse(self.sources["sqlglot/tokens.py"])
        tokenizer = next((node for node in tokens.body if isinstance(node, ast.ClassDef)
                          and node.name == "Tokenizer"), None)
        init_core = next((node for node in tokenizer.body if isinstance(node, ast.FunctionDef)
                          and node.name == "_init_core"), None) if tokenizer else None
        if init_core is None:
            return False
        transfers = [kw for call in ast.walk(init_core) if isinstance(call, ast.Call)
                     and isinstance(call.func, ast.Name) and call.func.id == "TokenizerCore"
                     for kw in call.keywords if kw.arg == "numeric_escapes"
                     and ast.unparse(kw.value) == "self.NUMERIC_ESCAPES"]
        if len(transfers) != 1:
            return False
        for name in ("_read_byte_escape", "_scan_numeric_escape"):
            method = next(node for node in core.body if isinstance(node, ast.FunctionDef)
                          and node.name == name)
            gets = [node for node in ast.walk(method) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                    and node.func.value is accesses[name][0]]
            if (len(gets) != 1 or len(gets[0].args) != 1 or gets[0].keywords
                    or ast.unparse(gets[0].args[0]) != "'0' if is_octal else peek"):
                return False
        extract = next(node for node in core.body if isinstance(node, ast.FunctionDef)
                       and node.name == "_extract_string")
        name_reads = [n for n in ast.walk(extract) if isinstance(n, ast.Name)
                      and n.id == "numeric_escapes" and isinstance(n.ctx, ast.Load)]
        guards = [n for n in ast.walk(extract) if isinstance(n, ast.BoolOp)
                  and isinstance(n.op, ast.And) and len(n.values) == 2
                  and n.values[1] in name_reads]
        return len(name_reads) == 1 and len(guards) == 1

    def numeric_pool_inputs_safe(self):
        """Check worker arguments before the profiling hook becomes active.

        The optimizer sends a function and fixture strings/dicts. The executor
        constructs its Expr in the traced parent before submitting it. Its
        worker initializer merely stores schema and table arguments.
        """
        files = {path for path, source in self.sources.items()
                 if path.startswith("tests/") and "ProcessPoolExecutor" in source}
        if files != {"tests/test_optimizer.py", "tests/test_executor.py"}:
            return False
        expected = {
            "tests/test_optimizer.py": "self.pool.submit(parse_and_optimize, func, sql, dialect, **func_kwargs)",
            "tests/test_executor.py": "pool.submit(mp_execute, parse_one(sql), args)",
        }
        for path, invocation in expected.items():
            tree = ast.parse(self.sources[path])
            submits = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                       and isinstance(node.func, ast.Attribute)
                       and node.func.attr == "submit"]
            if len(submits) != 1 or ast.unparse(submits[0]) != invocation:
                return False
            if path.endswith("test_executor.py"):
                initializer = next((node for node in tree.body
                                    if isinstance(node, ast.FunctionDef)
                                    and node.name == "initializer"), None)
                if (initializer is None or [ast.unparse(node) for node in initializer.body]
                        != ["global _schema, _tables", "_schema = schema", "_tables = tables"]):
                    return False
        return True

    def files_to_ids(self, files):
        return set().union(*(self.by_file.get(path, set()) for path in files))

    def select_ids(self, patch):
        selected = set()
        try:
            edits = sections(patch)
            for old, new, hunk in edits:
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
                        if changed_source_header(source, patched):
                            return self.all_ids
                        if changed_comment_text(hunk) and ast.dump(ast.parse(source)) != ast.dump(
                                ast.parse(patched)):
                            return self.all_ids
                    except (ValueError, SyntaxError, RecursionError):
                        return self.all_ids
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
                        # Class consumers in spawned workers are absent from
                        # the parent trace. A missing or incomplete child map
                        # cannot justify narrowing structural edits.
                        if self.pool_classes is None or not self.parent_class_map_valid:
                            return self.all_ids
                        if len(edits) == 1 and self.class_uses:
                            try:
                                edited_factory = class_factory_literal_edit(source, patched)
                            except (ValueError, SyntaxError, RecursionError):
                                edited_factory = None
                            if edited_factory:
                                (class_name, attr, _), factory = edited_factory
                                if self.safe_parser_closure_factory(old, class_name, attr, factory):
                                    key = old.removesuffix(".py").replace("/", ".") + ":" + class_name
                                    readers = self.factory_readers(old, class_name, attr)
                                    selected.update(self.class_uses[key], readers, self.readers,
                                                    self.subprocess, self.unmapped,
                                                    self.class_unprofiled, self.reflective_tests,
                                                    self.by_file.get(old, ()))
                                    continue
                        if len(edits) == 1 and self.class_uses:
                            try:
                                edited_lambda = class_lambda_edit(source, patched)
                            except (ValueError, SyntaxError, RecursionError):
                                edited_lambda = None
                            if edited_lambda:
                                class_name, attr, entry = edited_lambda
                                if self.safe_parser_dispatch_lambda(old, class_name, attr):
                                    module = old.removesuffix(".py").replace("/", ".")
                                    key = module + ":" + class_name
                                    readers = self.parser_lambda_readers(old, class_name, attr, entry)
                                    if readers is not None:
                                        selected.update(self.class_uses[key], readers, self.readers,
                                                        self.subprocess, self.unmapped,
                                                        self.class_unprofiled, self.reflective_tests,
                                                        self.by_file.get(old, ()))
                                        continue
                        if self.class_uses:
                            try:
                                edited_class = class_literal_edit(source, patched)
                            except (ValueError, SyntaxError, RecursionError):
                                edited_class = None
                            if edited_class:
                                if len(edits) != 1:
                                    return self.all_ids
                                (class_name, attr), before, after = edited_class
                                numeric_values = (len(edits) == 1 and attr == "NUMERIC_ESCAPES" and
                                    self.safe_numeric_escape_values(old, class_name, before, after))
                                module = old.removesuffix(".py").replace("/", ".").removesuffix(".__init__")
                                key = module + ":" + class_name
                                if numeric_values:
                                    parent_key = module + ":" + class_name.removesuffix(".Tokenizer")
                                    # The pinned metaclass and generator only read
                                    # keys or truthiness. A direct test of the
                                    # field may still observe changed values.
                                    explicit = {test for file, source in self.sources.items()
                                                if file.startswith("tests/")
                                                and (attr in source or "numeric_escapes" in source)
                                                for test in self.by_file.get(file, ())}
                                    key_users = set(self.class_uses[key])
                                    if (self.numeric_key_uses is not None
                                            and self.numeric_key_data_flow()):
                                        edits_to_keys = {entry for entry in before
                                                         if before[entry] != after[entry]}
                                        imported = set(self.numeric_key_uses["import_reads"].get(key, ()))
                                        if not edits_to_keys & imported:
                                            reads = self.numeric_key_uses["uses"].get(key, {})
                                            key_users = set().union(*(set(reads.get(entry, ()))
                                                                     for entry in edits_to_keys))
                                    selected.update(key_users, self.pool_classes["nested"],
                                                    explicit, self.reflective_tests, self.readers,
                                                    self.subprocess, self.unmapped,
                                                    self.class_unprofiled,
                                                    self.by_file.get(old, ()))
                                    continue
                                # A class instance made before a test may be
                                # reused without another observed constructor.
                                if (self.class_import_constructors is None
                                        or key in self.class_import_constructors):
                                    return self.all_ids
                                readers, import_read = self.class_readers(attr)
                                expression_schema = (attr == "arg_types" and
                                    self.safe_expression_arg_types(old, class_name, before, after))
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
