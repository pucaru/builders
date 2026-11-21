"""Index pristine static proofs for nested Tokenizer.NUMERIC_ESCAPES tables."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from impact import Impact, NUMERIC_SAFETY_INDEX_VERSION


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tests", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--map", type=Path, default=Path("impact.json.gz"))
    args = parser.parse_args()

    tests = json.loads(args.tests.read_bytes())["tests"]
    impact = Impact(tests, args.map, "pool-noop")
    rows = []
    for path, source in impact.sources.items():
        if not path.startswith("sqlglot/dialects/") or "NUMERIC_ESCAPES" not in source:
            continue
        tree = ast.parse(source)
        for parent in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            for tokenizer in (node for node in parent.body if isinstance(node, ast.ClassDef)
                              and node.name == "Tokenizer"):
                values = [statement.value for statement in tokenizer.body
                          if isinstance(statement, ast.Assign) and len(statement.targets) == 1
                          and isinstance(statement.targets[0], ast.Name)
                          and statement.targets[0].id == "NUMERIC_ESCAPES"]
                if len(values) != 1:
                    continue
                try:
                    value = ast.literal_eval(values[0])
                except (ValueError, TypeError):
                    continue
                class_name = parent.name + ".Tokenizer"
                rows.append([path, class_name,
                             impact.safe_numeric_escape_values(
                                 path, class_name, value, value)])

    rows.sort(key=lambda row: row[:2])
    ids = sorted(impact.all_ids)
    payload = {
        "version": NUMERIC_SAFETY_INDEX_VERSION,
        "impact_sha256": digest(args.map),
        "class_uses_sha256": digest(args.map.with_name("class-uses.json.gz")),
        "constructors_sha256": digest(
            args.map.with_name("class-import-constructors.json")),
        "pool_sha256": digest(args.map.with_name("pool-classes.json.gz")),
        "ids_sha256": hashlib.sha256(
            json.dumps(ids, separators=(",", ":")).encode()).hexdigest(),
        "entries_sha256": hashlib.sha256(
            json.dumps(rows, separators=(",", ":")).encode()).hexdigest(),
        "entries": rows,
    }
    with args.output.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            compressed.write(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    print(f"Wrote {len(rows)} numeric safety entries to {args.output}")


if __name__ == "__main__":
    main()
