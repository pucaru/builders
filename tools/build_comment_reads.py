"""Bind a complete pristine source-read audit to the selector's impact map."""
import argparse
import ast
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import pkgutil
import sys


def ids_digest(ids):
    return hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("profile", type=Path)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("impact", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--pool-profile", required=True, type=Path)
    ap.add_argument("--pool-map", required=True, type=Path)
    ap.add_argument("--checkout", required=True, type=Path)
    args = ap.parse_args()
    raw = json.loads(args.profile.read_text())
    manifest = json.loads(args.manifest.read_text())
    ids = {row["id"] for row in manifest["tests"]}
    by_test_file = {}
    for row in manifest["tests"]:
        by_test_file.setdefault(row["file"], set()).add(row["id"])
    if set(raw["collected"]) != ids | set(manifest["skipped"]):
        raise ValueError("profile omitted a pinned test")
    with gzip.open(args.impact, "rt") as handle:
        source = json.load(handle)["sources"]
    if not source["tests/test_typing.py"].count(".read_text("):
        raise ValueError("missing source-reader positive control")
    reads = {}
    for relative, events in raw["reads"].items():
        path = "sqlglot/" + relative
        if path not in source:
            raise ValueError(f"profile read an unknown source: {path}")
        selected = set()
        for context, callers in events:
            if not isinstance(context, str) or not isinstance(callers, list):
                raise ValueError("malformed read event")
            if callers and callers[0].startswith("<frozen importlib."):
                # Importlib reads source only to compile code. The selector
                # separately proves recursively identical executable code;
                # location metadata is handled by the pinned observer audit.
                continue
            if not context:
                selected = ids  # import/collection reads may affect every test
            elif context not in ids and context not in manifest["skipped"]:
                raise ValueError("unknown test context")
            elif context in ids:
                # A read in setup can seed other tests in the same module.
                selected.update(by_test_file[context.split("::", 1)[0]])
        reads[path] = sorted(selected)
    child = json.loads(args.pool_profile.read_text())
    with gzip.open(args.pool_map, "rt") as handle:
        pool = json.load(handle)
    records = child["records"]
    if (child["tasks"] != pool["tasks"] or child["callers"] != pool["callers"]
            or len(records) != pool["tasks"]
            or {row["number"] for row in records} != set(range(pool["tasks"]))
            or not isinstance(child["bootstrap"], list)):
        raise ValueError("incomplete or mismatched process-pool read trace")
    caller_tasks = {}
    for record in records:
        context = record["nodeid"]
        caller_tasks[context] = caller_tasks.get(context, 0) + 1
        if context not in ids:
            raise ValueError("unknown process-pool caller")
        for relative, callers in record["reads"]:
            path = "sqlglot/" + relative
            if path not in source or not isinstance(callers, list):
                raise ValueError("unexpected child source read")
            if callers and callers[0].startswith("<frozen importlib."):
                continue
            reads.setdefault(path, [])
            reads[path] = sorted(set(reads[path]) | by_test_file[context.split("::", 1)[0]])
    if caller_tasks != pool["caller_tasks"]:
        raise ValueError("changed process-pool task distribution")
    for event in child["bootstrap"]:
        path = "sqlglot/" + event["path"]
        callers = event["callers"]
        if path not in source or not isinstance(callers, list):
            raise ValueError("unexpected worker bootstrap source read")
        if callers and callers[0].startswith("<frozen importlib."):
            continue
        # The event predates assignment to a particular test task. A module
        # import or initializer could persist state across all pool callers.
        reads[path] = sorted(set(reads.get(path, ())) | set(pool["callers"]))
    if not any(path.startswith("sqlglot/typing/") and ids_for_file
               for path, ids_for_file in reads.items()):
        raise ValueError("profile missed test_typing's known source reads")
    # Source-position metadata is observable without opening .py files. Find
    # every pinned test that uses a line-sensitive API. The one co_consts user
    # compares annotators in the pristine typing metadata; enumerate their
    # actual code filenames instead of assuming a package boundary.
    sensitive_attrs = {"co_firstlineno", "co_linetable", "co_lnotab",
                       "co_lines", "co_positions", "f_lineno", "tb_lineno",
                       "co_consts", "getsource", "getsourcelines"}
    sensitive_names = {"linecache", "traceback", "getsource", "getsourcelines"}
    risk = {}
    for path, text in source.items():
        if not (path.startswith("tests/") or path.startswith("sqlglot/")):
            continue
        tree = ast.parse(text)
        found = {node.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Attribute) and node.attr in sensitive_attrs}
        found.update(node.id for node in ast.walk(tree)
                     if isinstance(node, ast.Name) and node.id in sensitive_names)
        found.update(node.value for node in ast.walk(tree)
                     if isinstance(node, ast.Constant) and isinstance(node.value, str)
                     and node.value in sensitive_attrs | sensitive_names)
        found.update(node.module for node in ast.walk(tree)
                     if isinstance(node, ast.ImportFrom) and node.module in sensitive_names)
        found.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                     for alias in node.names if alias.name in sensitive_names)
        if found:
            risk[path] = found
    typing_test = "tests/test_typing.py"
    typing_ids = by_test_file.get(typing_test, set())
    if (not typing_ids or risk.pop(typing_test, None) != {"co_consts"}):
        raise ValueError("typing metadata observer changed; review required")
    global_ids = set()
    for path in risk:
        global_ids.update(by_test_file.get(path, ids if path.startswith("sqlglot/") else ()))

    checkout = args.checkout.resolve()
    sys.path.insert(0, str(checkout))
    typing_module = importlib.import_module("sqlglot.typing")
    typing_dir = Path(typing_module.__file__).resolve().parent
    if typing_dir != checkout / "sqlglot" / "typing":
        raise ValueError("typing import did not use the pinned checkout")
    line_observers = {}
    modules = [typing_module] + [importlib.import_module(f"sqlglot.typing.{entry.name}")
                                 for entry in pkgutil.iter_modules([str(typing_dir)])]
    for module in modules:
        metadata = getattr(module, "EXPRESSION_METADATA", {})
        if not isinstance(metadata, dict):
            raise ValueError("unexpected typing metadata")
        for entry in metadata.values():
            if not isinstance(entry, dict):
                continue
            annotator = entry.get("annotator")
            if not hasattr(annotator, "__code__"):
                continue
            filename = Path(annotator.__code__.co_filename).resolve()
            try:
                path = filename.relative_to(checkout).as_posix()
            except ValueError:
                global_ids.update(typing_ids)
                continue
            if path not in source:
                global_ids.update(typing_ids)
                continue
            line_observers.setdefault(path, set()).update(typing_ids)
    line_observers = {path: sorted(ids_for_file)
                      for path, ids_for_file in sorted(line_observers.items())}
    observer = {"line_observers": line_observers,
                "global_line_observers": sorted(global_ids)}
    read_bytes = json.dumps(reads, sort_keys=True, separators=(",", ":")).encode()
    observer_bytes = json.dumps(observer, sort_keys=True, separators=(",", ":")).encode()
    payload = {"impact_sha256": hashlib.sha256(args.impact.read_bytes()).hexdigest(),
               "pool_sha256": hashlib.sha256(args.pool_map.read_bytes()).hexdigest(),
               "ids_sha256": ids_digest(ids),
               "reads_sha256": hashlib.sha256(read_bytes).hexdigest(), "reads": reads,
               "observer_sha256": hashlib.sha256(observer_bytes).hexdigest(), **observer}
    args.output.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"{len(reads)} source files read by tests, {args.output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
