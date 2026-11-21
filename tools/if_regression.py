"""Label fresh one-line if-condition mutations against the full pinned suite."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import shutil
import sys

from regression import label, write_patch


CASES = {
    "bigquery-table-identifiers": (
        "sqlglot/parsers/bigquery.py",
        "if isinstance(table.this, exp.Identifier) and any(\".\" in p.name for p in table.parts):",
        "if isinstance(table.this, exp.Identifier) or any(\".\" in p.name for p in table.parts):",
    ),
    "bigquery-catalog": (
        "sqlglot/parsers/bigquery.py",
        "if not table.catalog:",
        "if table.catalog:",
    ),
    "mysql-limit": (
        "sqlglot/parsers/mysql.py",
        "if self._match_text_seq(\"LIMIT\"):",
        "if not self._match_text_seq(\"LIMIT\"):",
    ),
    "scope-setop": (
        "sqlglot/optimizer/scope.py",
        "if prev_scope is None and isinstance(inner, exp.SetOperation):",
        "if prev_scope is None or isinstance(inner, exp.SetOperation):",
    ),
    "simplify-date-delta": (
        "sqlglot/optimizer/simplify.py",
        "if delta is None or value is None:",
        "if delta is None and value is None:",
    ),
    "generator-ensure-bools": (
        "sqlglot/generator.py",
        "if self.ENSURE_BOOLS:",
        "if not self.ENSURE_BOOLS:",
    ),
}


def main():
    root, manifest_path, output = map(lambda x: Path(x).resolve(), sys.argv[1:4])
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
    _, clean = label(root, logs, "clean", {}, manifest, 900, 2)
    if clean["failing"]:
        raise RuntimeError(f"clean checkout failures: {clean['failing']}")
    edits = {}
    for name, (path, before, after) in CASES.items():
        if name not in requested:
            continue
        old = (root / path).read_text()
        if old.count(before) != 1:
            raise RuntimeError(f"ambiguous mutation {name}: {old.count(before)} matches")
        new = old.replace(before, after, 1)
        edits[name] = {path: new}
        write_patch(root, edits[name], patches / f"{name}.patch")
    answer_path = output / "answers.json"
    result = json.loads(answer_path.read_text())["commits"] if answer_path.exists() else {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(label, root, logs, name, files, manifest, 900, 2)
                   for name, files in edits.items()]
        for future in as_completed(futures):
            name, row = future.result()
            result[name] = row
            print(f"{name}: {len(row['failing'])} failing, {row['seconds']}s", flush=True)
    answer_path.write_text(json.dumps({"commits": result}, sort_keys=True))


if __name__ == "__main__":
    main()
