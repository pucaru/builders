"""Generate benign regressions and label them with the full pinned pytest suite."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import ast
import difflib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time


def change_body(root, path, name, *, preserve_docstring=False):
    source = (root / path).read_text()
    nodes = [node for node in ast.walk(ast.parse(source))
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
             and not (len(node.body) == 1 and isinstance(node.body[0], ast.Expr)
                      and isinstance(node.body[0].value, ast.Constant)
                      and node.body[0].value.value is Ellipsis)]
    node = nodes[0]
    first = node.body[int(preserve_docstring and ast.get_docstring(node) is not None)]
    lines = source.splitlines(keepends=True)
    lines.insert(first.lineno - 1, " " * first.col_offset + "raise ValueError('regression case')\n")
    return "".join(lines)


def cases(root, seed):
    targets = [
        ("sqlglot/time.py", "subsecond_precision"),
        ("sqlglot/time.py", "format_time"),
        ("sqlglot/jsonpath.py", "parse"),
        ("sqlglot/optimizer/simplify.py", "simplify"),
        ("sqlglot/optimizer/annotate_types.py", "annotate_types"),
        ("sqlglot/optimizer/normalize_identifiers.py", "normalize_identifiers"),
        ("sqlglot/executor/__init__.py", "execute"),
        ("sqlglot/transforms.py", "eliminate_qualify"),
        ("sqlglot/transforms.py", "eliminate_distinct_on"),
        ("sqlglot/__init__.py", "parse_one"),
        ("sqlglot/__init__.py", "transpile"),
        ("sqlglot/dialects/dialect.py", "get_or_raise"),
    ]
    random.Random(seed).shuffle(targets)
    for path, name in targets:
        yield name, {path: change_body(root, path, name)}
    for path, name in (
        ("sqlglot/time.py", "subsecond_precision"),
        ("sqlglot/executor/__init__.py", "execute"),
        ("sqlglot/jsonpath.py", "parse"),
        ("sqlglot/transforms.py", "eliminate_distinct_on"),
    ):
        yield f"body-{name}", {path: change_body(root, path, name, preserve_docstring=True)}
    parser = "sqlglot/parser.py"
    yield "comment", {parser: (root / parser).read_text() + "\n# local evaluation\n"}
    yield "syntax", {parser: (root / parser).read_text() + "\ndef invalid(\n"}
    init = "sqlglot/__init__.py"
    yield "lazy-import", {
        init: (root / init).read_text() + "\nimport sqlglot.dialects.mysql\n",
    }
    first = targets[0]
    second = next(target for target in targets[1:] if target[0] != first[0])
    yield "multi-file", {path: change_body(root, path, name) for path, name in (first, second)}
    fixture = "tests/fixtures/optimizer/simplify.sql"
    fixture_text = (root / fixture).read_text()
    changed = re.sub(r"(?i)\bSELECT\b", "SELECT deliberately_changed,", fixture_text, count=1)
    if fixture_text == changed:
        raise ValueError("fixture mutation did not apply")
    yield "fixture", {fixture: changed}
    path = "sqlglot/time.py"
    yield "rename", {path: None, "sqlglot/time_moved.py": (root / path).read_text()}


def write_patch(root, edits, destination):
    if len(edits) == 2 and list(edits.values()).count(None) == 1:
        old, new = sorted(edits, key=lambda path: edits[path] is not None)
        if (root / old).read_text() == edits[new] and not (root / new).exists():
            destination.write_text(
                f"diff --git a/{old} b/{new}\nsimilarity index 100%\n"
                f"rename from {old}\nrename to {new}\n"
            )
            return
    chunks = []
    for path, content in edits.items():
        original = (root / path).read_text() if (root / path).is_file() else None
        chunks.append(f"diff --git a/{path} b/{path}\n")
        if original is None:
            chunks.append("new file mode 100644\n")
        if content is None:
            chunks.append("deleted file mode 100644\n")
        for line in difflib.unified_diff(
            (original or "").splitlines(keepends=True),
            (content or "").splitlines(keepends=True),
            f"a/{path}" if original is not None else "/dev/null",
            f"b/{path}" if content is not None else "/dev/null",
        ):
            chunks.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
    destination.write_text("".join(chunks))


def label(root, logs, name, edits, manifest, timeout, pool_cpus):
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="blast-label-") as temp:
        checkout = Path(temp) / "sqlglot"
        shutil.copytree(root, checkout, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".pytest_cache"))
        for path, content in edits.items():
            if content is None:
                (checkout / path).unlink()
            else:
                (checkout / path).write_text(content)
        report = Path(temp) / "outcomes.json"
        env = dict(os.environ, BLAST_OUTCOMES=str(report), SKIP_INTEGRATION="0",
                   PYTHONPATH=os.pathsep.join([str(checkout), str(Path(__file__).resolve().parent)]),
                   PYTHON_CPU_COUNT=str(pool_cpus),
                   PATH=os.pathsep.join([str(Path(sys.executable).parent), os.environ["PATH"]]))
        with (logs / f"{name}.log").open("w") as log:
            execution = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "tests", "--continue-on-collection-errors",
                 "--tb=no", "--timeout=180", "-p", "outcomes"],
                cwd=checkout, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout,
            )
        if execution.returncode not in {0, 1, 2, 5} or not report.exists():
            raise RuntimeError(f"label failed for {name}. See {logs / (name + '.log')}")
        data = json.loads(report.read_text())
        failed = set(data["failed"])
        collected = set(data["collected"])
        errors = data["collection_errors"]
        result = []
        for test in manifest:
            if (test["id"] in failed or test["id"] not in collected or any(
                    test["file"] == node or test["file"].startswith(node + "/") or node in ("", ".")
                    for node in errors)):
                result.append(test["number"])
        if failed and not result:
            raise RuntimeError(f"Unmapped pytest failures for {name}: {failed}")
    return name, {"kind": "code", "failing": result, "seconds": round(time.monotonic() - started, 3)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=44793)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--pool-cpus", type=int, default=2)
    parser.add_argument("--cases", nargs="+", help="Run just these case names after the clean check")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    args.output.mkdir()
    logs = args.output / "logs"
    patches = args.output / "data" / "commits"
    logs.mkdir()
    (args.output / "labels").mkdir()
    patches.mkdir(parents=True)
    shutil.copyfile(args.manifest, patches.parent / "tests.json")
    manifest = json.loads(args.manifest.read_text())["tests"]
    root = args.checkout.resolve()
    _, clean = label(root, logs, "clean", {}, manifest, args.timeout, args.pool_cpus)
    if clean["failing"]:
        raise RuntimeError(f"Pristine suite disagrees with manifest: {clean['failing']}")
    all_cases = dict(cases(root, args.seed))
    edits_by_name = list(all_cases.items()) if not args.cases else [
        (name, all_cases[name]) for name in args.cases
    ]
    for name, edits in edits_by_name:
        write_patch(root, edits, patches / f"{name}.patch")
    results = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        tasks = [pool.submit(label, root, logs, name, edits, manifest, args.timeout, args.pool_cpus)
                 for name, edits in edits_by_name]
        for task in as_completed(tasks):
            name, result = task.result()
            results[name] = result
            (args.output / "labels" / f"{name}.json").write_text(json.dumps(result))
            print(f"{name}: {len(result['failing'])} failures in {result['seconds']} s", flush=True)
    (args.output / "answers.json").write_text(json.dumps({"commits": results}, sort_keys=True))


if __name__ == "__main__":
    main()
