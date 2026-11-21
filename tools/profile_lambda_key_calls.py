"""Observe pristine parser lambda executions by pytest node and worker task."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading

import pytest

from lambda_key_child import run_task


class Trace:
    def __init__(self, root):
        self.root = root
        self.prefix = str(root / "sqlglot") + os.sep
        self.current = ""
        self.phase = ""
        self.calls = defaultdict(set)
        self.shared = defaultdict(set)
        self.submitted = {}
        self.submitted_setup = set()
        self.original_submit = ProcessPoolExecutor.submit
        self.collected = None

    def pytest_collection_finish(self, session):
        self.collected = {item.nodeid for item in session.items}

    def profile(self, frame, event, arg):
        if event != "call":
            return
        code = frame.f_code
        if code.co_name != "<lambda>" or not code.co_filename.startswith(self.prefix):
            return
        path = Path(code.co_filename).relative_to(self.root).as_posix()
        if not path.startswith("sqlglot/parsers/"):
            return
        key = (path, code.co_firstlineno, code.co_qualname)
        self.calls[key].add(self.current)
        if self.phase in {"setup", "teardown"} and self.current:
            self.shared[key].add(self.current.rsplit("::", 1)[0])

    def install_pool(self, monkeypatch):
        def submit(pool, function, /, *args, **kwargs):
            number = len(self.submitted)
            self.submitted[number] = self.current
            if self.phase in {"setup", "teardown"}:
                self.submitted_setup.add(number)
            return self.original_submit(pool, run_task, number, self.current,
                                        function, args, kwargs)
        monkeypatch.setattr(ProcessPoolExecutor, "submit", submit)

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_protocol(self, item):
        self.current = item.nodeid
        try:
            return (yield)
        finally:
            self.current = ""

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_setup(self, item):
        self.phase = "setup"
        try:
            return (yield)
        finally:
            self.phase = ""

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_teardown(self, item, nextitem):
        self.phase = "teardown"
        try:
            return (yield)
        finally:
            self.phase = ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("checkout", type=Path)
    ap.add_argument("tests_json", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--impact-map", type=Path, default=Path("impact.json.gz"))
    args = ap.parse_args()
    root, output = args.checkout.resolve(), args.output.resolve()
    impact_digest = hashlib.sha256(args.impact_map.resolve().read_bytes()).hexdigest()
    manifest = json.loads(args.tests_json.resolve().read_text())
    known = {row["id"] for row in manifest["tests"]}
    expected_collection = known | set(manifest["skipped"])
    by_class = defaultdict(set)
    for nodeid in known:
        by_class[nodeid.rsplit("::", 1)[0]].add(nodeid)
    os.chdir(root)
    sys.path.insert(0, str(root))
    if "sqlglot" in sys.modules:
        raise RuntimeError("SQLGlot loaded before trace")
    trace = Trace(root)
    with tempfile.TemporaryDirectory(prefix="lambda-key-trace-") as temp:
        os.environ["BLAST_LAMBDA_KEY_DIR"] = temp
        os.environ["BLAST_LAMBDA_KEY_ROOT"] = str(root)
        hook_dir = Path(temp) / "hook"
        hook_dir.mkdir()
        shutil.copyfile(Path(__file__).with_name("lambda_key_sitecustomize.py"),
                        hook_dir / "sitecustomize.py")
        os.environ["PYTHONPATH"] = os.pathsep.join(
            [str(hook_dir), str(root), str(Path(__file__).resolve().parent)])
        previous = sys.getprofile()
        sys.setprofile(trace.profile)
        threading.setprofile(trace.profile)
        try:
            with pytest.MonkeyPatch.context() as monkeypatch:
                trace.install_pool(monkeypatch)
                result = pytest.main(["-q", "tests", "--tb=no"], plugins=[trace])
        finally:
            sys.setprofile(previous)
            threading.setprofile(None)
        if result:
            return result
        if trace.collected != expected_collection:
            raise ValueError("pristine test collection differs from manifest")
        records = {}
        for path in Path(temp).glob("task-*.json"):
            row = json.loads(path.read_text())
            number = row["number"]
            if number in records or row["nodeid"] != trace.submitted.get(number):
                raise ValueError("duplicate/mismatched task")
            records[number] = row
        if set(records) != set(trace.submitted):
            raise ValueError("missing pool task records")
        booted = set()
        early = set()
        for path in Path(temp).glob("startup-*.jsonl"):
            lines = [json.loads(s) for s in path.read_text().splitlines()]
            if not lines or set(lines[0]) != {"startup"}:
                raise ValueError("incomplete worker startup trace")
            booted.add(lines[0]["startup"])
            early.update(tuple(row["key"]) for row in lines[1:])
        if {row["pid"] for row in records.values()} - booted:
            raise ValueError("worker missing startup hook")
        for key, scopes in trace.shared.items():
            for scope in scopes:
                trace.calls[key].update(by_class[scope])
        for row in records.values():
            for key in row["calls"]:
                trace.calls[tuple(key)].add(row["nodeid"])
                if row["number"] in trace.submitted_setup:
                    trace.shared[tuple(key)].add(row["nodeid"].rsplit("::", 1)[0])
        if any(not ids <= known | {""} for ids in trace.calls.values()):
            raise ValueError("unknown contexts")
        import_calls = {key for key, ids in trace.calls.items() if "" in ids} | early
        for ids in trace.calls.values():
            ids.discard("")
        counts = {}
        for nodeid in trace.submitted.values():
            counts[nodeid] = counts.get(nodeid, 0) + 1
        payload = {
            "calls": [[*key, sorted(ids)] for key, ids in sorted(trace.calls.items())],
            "import_calls": sorted(import_calls),
            "shared_calls": sorted(trace.shared),
            "tasks": len(trace.submitted), "callers": sorted(counts),
            "caller_tasks": counts,
            "impact_sha256": impact_digest,
        }
        data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with gzip.GzipFile(output, "wb", mtime=0) as f:
            f.write(data)
        print(len(known), "tests", len(records), "tasks", len(trace.calls), "lambdas", len(import_calls), "import calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
