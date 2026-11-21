"""Trace SQLGlot class receivers in pristine ProcessPoolExecutor tasks.

Every submitted task gets a numbered record. Incomplete traces are rejected
instead of silently treating an unobserved class as unused.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
import os
from pathlib import Path
import sys
import tempfile

import pytest

from pool_class_child import run_task


class PoolClassTrace:
    def __init__(self):
        self.current = ""
        self.submitted = {}
        self.original_submit = ProcessPoolExecutor.submit

    def install(self, monkeypatch):
        def submit_with_test(pool, function, /, *args, **kwargs):
            number = len(self.submitted)
            self.submitted[number] = self.current
            return self.original_submit(pool, run_task, number, self.current,
                                        function, args, kwargs)

        monkeypatch.setattr(ProcessPoolExecutor, "submit", submit_with_test)

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_protocol(self, item):
        self.current = item.nodeid
        try:
            return (yield)
        finally:
            self.current = ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    parser.add_argument("tests_json", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tests", nargs="+", default=["tests/test_optimizer.py",
                                                 "tests/test_executor.py"])
    args = parser.parse_args()
    root = args.checkout.resolve()
    manifest = json.loads(args.tests_json.resolve().read_text())["tests"]
    known = {test["id"] for test in manifest}
    output = args.output.resolve()
    os.chdir(root)
    sys.path.insert(0, str(root))
    trace = PoolClassTrace()
    with tempfile.TemporaryDirectory(prefix="blast-pool-classes-") as temp:
        os.environ["BLAST_POOL_CLASS_DIR"] = temp
        os.environ["PYTHONPATH"] = os.pathsep.join(
            [str(root), str(Path(__file__).resolve().parent)])
        with pytest.MonkeyPatch.context() as monkeypatch:
            trace.install(monkeypatch)
            result = pytest.main(["-q", *args.tests, "--tb=no"], plugins=[trace])
        if result:
            return result
        records = {}
        for path in Path(temp).glob("*.json"):
            record = json.loads(path.read_text())
            number = record["number"]
            if number in records or record["nodeid"] != trace.submitted.get(number):
                raise ValueError(f"mismatched pool record {path}")
            records[number] = record
        if set(records) != set(trace.submitted):
            raise ValueError(f"missing pool records: {set(trace.submitted) - set(records)}")
        classes = {}
        nested = set()
        for record in records.values():
            nodeid = record["nodeid"]
            if nodeid not in known:
                raise ValueError(f"unknown pool caller {nodeid}")
            if record["nested"]:
                nested.add(nodeid)
            for key in record["classes"]:
                classes.setdefault(key, set()).add(nodeid)
        caller_tasks = {}
        for nodeid in trace.submitted.values():
            caller_tasks[nodeid] = caller_tasks.get(nodeid, 0) + 1
        payload = {"classes": {key: sorted(ids) for key, ids in sorted(classes.items())},
                   "callers": sorted(caller_tasks), "caller_tasks": caller_tasks,
                   "nested": sorted(nested), "tasks": len(trace.submitted)}
        content = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if output.suffix == ".gz":
            with gzip.GzipFile(output, "wb", mtime=0) as stream:
                stream.write(content)
        else:
            output.write_bytes(content)
        print(f"{len(trace.submitted)} tasks, {len(payload['callers'])} callers, "
              f"{len(classes)} classes, {len(nested)} nested processes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
