"""Label fresh parser dispatch-body changes on pristine pinned SQLGlot."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys

from regression import label, write_patch


def main():
    root = Path(sys.argv[1]).resolve()
    manifest_path = Path(sys.argv[2]).resolve()
    output = Path(sys.argv[3]).resolve()
    output.mkdir()
    (output / "logs").mkdir()
    patches = output / "data" / "commits"
    patches.mkdir(parents=True)
    (output / "data" / "tests.json").write_bytes(manifest_path.read_bytes())
    cases = {
        "clickhouse-length-argument": (
            "sqlglot/parsers/clickhouse.py",
            '"LENGTH": lambda args: exp.Length(this=seq_get(args, 0), binary=True)',
            '"LENGTH": lambda args: exp.Length(this=seq_get(args, 1), binary=True)',
        ),
        "clickhouse-trim-direction": (
            "sqlglot/parsers/clickhouse.py",
            '"TRIMRIGHT": lambda args: parser.build_trim(args, is_left=False)',
            '"TRIMRIGHT": lambda args: parser.build_trim(args, is_left=True)',
        ),
        "exasol-bit-not-argument": (
            "sqlglot/parsers/exasol.py",
            '"BIT_NOT": lambda args: exp.BitwiseNot(this=seq_get(args, 0))',
            '"BIT_NOT": lambda args: exp.BitwiseNot(this=seq_get(args, 2))',
        ),
        "dremio-split-mode": (
            "sqlglot/parsers/dremio.py",
            "mode=seq_get(args, 2),",
            "mode=seq_get(args, 0),",
        ),
    }
    if len(sys.argv) > 4:
        cases = {name: cases[name] for name in sys.argv[4:]}
    manifest = json.loads(manifest_path.read_text())["tests"]
    work = {}
    for name, (path, old, new) in cases.items():
        source = (root / path).read_text()
        if source.count(old) != 1:
            raise ValueError((name, "expected unique source anchor", source.count(old)))
        edits = {path: source.replace(old, new, 1)}
        write_patch(root, edits, patches / (name + ".patch"))
        work[name] = edits
    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = [pool.submit(label, root, output / "logs", name, edits, manifest, 900, 2)
                 for name, edits in work.items()]
        for task in as_completed(tasks):
            name, result = task.result()
            results[name] = result
            print(name, len(result["failing"]), result["seconds"], flush=True)
    (output / "answers.json").write_text(json.dumps({"commits": results}, sort_keys=True))


if __name__ == "__main__":
    main()
