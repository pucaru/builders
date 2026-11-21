"""Full-suite labels for pristine-source comment and mixed-edit controls."""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import shutil

from regression import label, write_patch


def insert(root, path, function, lines):
    source = (root / path).read_text()
    candidates = [node for node in ast.walk(ast.parse(source))
                  if isinstance(node, ast.FunctionDef) and node.name == function]
    if len(candidates) != 1:
        raise ValueError(f"function {function} is not unique in {path}")
    node = candidates[0]
    first = node.body[0]
    source_lines = source.splitlines(keepends=True)
    prefix = " " * first.col_offset
    source_lines[first.lineno - 1:first.lineno - 1] = [prefix + line + "\n" for line in lines]
    result = "".join(source_lines)
    compile(result, path, "exec")
    return {path: result}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("checkout", type=Path)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--cases", nargs="+")
    args = ap.parse_args()
    root = args.checkout.resolve()
    output = args.output.resolve()
    output.mkdir()
    logs = output / "logs"
    commits = output / "data" / "commits"
    logs.mkdir()
    commits.mkdir(parents=True)
    shutil.copyfile(args.manifest, commits.parent / "tests.json")
    manifest = json.loads(args.manifest.read_text())["tests"]
    cases = {
        "oracle_comment": insert(root, "sqlglot/generators/oracle.py", "variance_sql", [
            "# A generator comment has no executable expression."]),
        "typing_comment": insert(root, "sqlglot/typing/duckdb.py", "_annotate_at_time_zone", [
            "# A source-reading test observes this module."]),
        "mixed_comment_code": insert(root, "sqlglot/time.py", "format_time", [
            "# This edit also changes behavior.", "raise ValueError('mixed comment control')"]),
    }
    if args.cases:
        cases = {name: cases[name] for name in args.cases}
    for name, edits in cases.items():
        write_patch(root, edits, commits / (name + ".patch"))
    results = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        tasks = [pool.submit(label, root, logs, name, edits, manifest, 900, 2)
                 for name, edits in cases.items()]
        for task in as_completed(tasks):
            name, result = task.result()
            results[name] = result
            print(name, len(result["failing"]), result["seconds"], flush=True)
    (output / "answers.json").write_text(json.dumps({"commits": results}, sort_keys=True))


if __name__ == "__main__":
    main()
