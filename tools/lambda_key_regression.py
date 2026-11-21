"""Label two independent parser dispatch lambda edits with the pinned full suite."""
import json
from pathlib import Path
import shutil
import sys

from regression import label, write_patch


CASES = {
    "duckdb-sha256-length": (
        "sqlglot/parsers/duckdb.py",
        '"SHA256": lambda args: exp.SHA2(this=seq_get(args, 0), length=exp.Literal.number(256)),',
        '"SHA256": lambda args: exp.SHA2(this=seq_get(args, 0), length=exp.Literal.number(512)),',
    ),
    "presto-bitwise-not": (
        "sqlglot/parsers/presto.py",
        '"BITWISE_NOT": lambda args: exp.BitwiseNot(this=seq_get(args, 0)),',
        '"BITWISE_NOT": lambda args: exp.BitwiseNot(this=seq_get(args, 1)),',
    ),
    "bigquery-length-arg": (
        "sqlglot/parsers/bigquery.py",
        '"LENGTH": lambda args: exp.Length(this=seq_get(args, 0), binary=True),',
        '"LENGTH": lambda args: exp.Length(this=seq_get(args, 1), binary=True),',
    ),
}


def main():
    root, manifest_path, output = map(lambda value: Path(value).resolve(), sys.argv[1:4])
    requested = set(sys.argv[4:]) if len(sys.argv) > 4 else set(CASES)
    if not requested <= CASES.keys():
        raise ValueError(f"unknown cases: {requested - CASES.keys()}")
    output.mkdir(exist_ok=True)
    logs = output / "logs"
    patches = output / "data" / "commits"
    logs.mkdir(exist_ok=True)
    patches.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest_path, patches.parent / "tests.json")
    manifest = json.loads(manifest_path.read_text())["tests"]
    answers_path = output / "answers.json"
    results = json.loads(answers_path.read_text())["commits"] if answers_path.exists() else {}
    for name, (path, before, after) in CASES.items():
        if name not in requested:
            continue
        old = (root / path).read_text()
        if old.count(before) != 1:
            raise ValueError(f"ambiguous pristine mutation {name}")
        new = old.replace(before, after, 1)
        write_patch(root, {path: new}, patches / f"{name}.patch")
        key, result = label(root, logs, name, {path: new}, manifest, 900, 2)
        results[key] = result
        answers_path.write_text(json.dumps({"commits": results}, sort_keys=True))
        print(f"{name}: {len(result['failing'])} failing in {result['seconds']}s", flush=True)


if __name__ == "__main__":
    main()
