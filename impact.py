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


class Impact:
    def __init__(self, tests, map_path, mode):
        with gzip.open(map_path, "rt") as handle:
            self.maps = json.load(handle)
        fixture_path = map_path.with_name("fixture-reads.json")
        self.fixture_reads = json.loads(fixture_path.read_text()) if fixture_path.exists() else {}
        self.tests = tests
        self.mode = mode
        self.all_ids = {test["id"] for test in tests}
        self.by_file = {}
        for test in tests:
            self.by_file.setdefault(test["file"], set()).add(test["id"])
        self.sources = self.maps["sources"]
        self.static = self.maps["static"]
        self.lines = self.maps.get("lines", {})
        self.contexts = self.maps.get("contexts", [])
        self.readers = self.files_to_ids(self.maps["source_readers"])
        self.subprocess = set(self.maps.get("subprocess", []))
        self.unmapped = self.all_ids.difference(
            test for group in self.contexts for test in group
        )

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
                    selected.update(readers, self.subprocess, self.unmapped)
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
