"""Build a pristine-source index for Parser.FUNCTIONS lambda readers."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from impact import Impact, PARSER_LAMBDA_READER_INDEX_VERSION


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
        if not path.startswith("sqlglot/parsers/") or "FUNCTIONS" not in source:
            continue
        tree = ast.parse(source)
        for owner in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            if not impact.safe_parser_dispatch_lambda(path, owner.name, "FUNCTIONS"):
                continue
            fields = []
            for statement in owner.body:
                if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                        and isinstance(statement.targets[0], ast.Name)
                        and statement.targets[0].id == "FUNCTIONS"):
                    fields.append(statement.value)
                elif (isinstance(statement, ast.AnnAssign) and statement.simple == 1
                        and isinstance(statement.target, ast.Name)
                        and statement.target.id == "FUNCTIONS"):
                    fields.append(statement.value)
            if len(fields) != 1 or not isinstance(fields[0], ast.Dict):
                continue
            entries = sorted({key.value for key, value in zip(fields[0].keys, fields[0].values)
                              if isinstance(key, ast.Constant) and type(key.value) is str
                              and isinstance(value, ast.Lambda)})
            for entry in entries:
                readers = impact.parser_lambda_readers(path, owner.name, "FUNCTIONS", entry)
                rows.append([path, owner.name, "FUNCTIONS", entry,
                             None if readers is None else sorted(readers)])

    rows.sort(key=lambda row: row[:4])
    import_path = args.map.with_name("parser-lambda-import-calls.json")
    ids = sorted(impact.all_ids)
    payload = {
        "version": PARSER_LAMBDA_READER_INDEX_VERSION,
        "impact_sha256": digest(args.map),
        "import_calls_sha256": digest(import_path),
        "ids_sha256": hashlib.sha256(
            json.dumps(ids, separators=(",", ":")).encode()
        ).hexdigest(),
        "entries_sha256": hashlib.sha256(
            json.dumps(rows, separators=(",", ":")).encode()
        ).hexdigest(),
        "entries": rows,
    }
    with args.output.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            compressed.write(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    print(f"Wrote {len(rows)} parser lambda reader entries to {args.output}")


if __name__ == "__main__":
    main()
