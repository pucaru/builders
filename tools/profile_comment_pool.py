"""Run every pinned process-pool test with task-complete child source-read audit."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import sys
import tempfile
import shutil

import pytest

from pool_comment_child import run_task


class PoolReads:
    def __init__(self):
        self.current = ""
        self.submitted = {}
        self.original_submit = ProcessPoolExecutor.submit

    def install(self, monkeypatch):
        def submit(pool, function, /, *args, **kwargs):
            number = len(self.submitted)
            self.submitted[number] = self.current
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("checkout", type=Path)
    ap.add_argument("tests_json", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    root = args.checkout.resolve()
    manifest = json.loads(args.tests_json.read_text())
    known = {row["id"] for row in manifest["tests"]}
    output = args.output.resolve()
    os.chdir(root)
    sys.path.insert(0, str(root))
    plugin = PoolReads()
    with tempfile.TemporaryDirectory(prefix="blast-comment-pool-") as temp:
        os.environ["BLAST_COMMENT_POOL_DIR"] = temp
        os.environ["BLAST_COMMENT_SOURCE_PREFIX"] = str(root / "sqlglot") + os.sep
        hook_dir = Path(temp) / "hook"
        hook_dir.mkdir()
        shutil.copyfile(Path(__file__).with_name("comment_sitecustomize.py"),
                        hook_dir / "sitecustomize.py")
        os.environ["PYTHONPATH"] = os.pathsep.join(
            [str(hook_dir), str(root), str(Path(__file__).resolve().parent)])
        with pytest.MonkeyPatch.context() as monkeypatch:
            plugin.install(monkeypatch)
            rc = pytest.main(["-q", "tests/test_optimizer.py", "tests/test_executor.py",
                              "--tb=no"], plugins=[plugin])
        if rc:
            return rc
        records = {}
        for path in Path(temp).glob("*.json"):
            data = json.loads(path.read_text())
            number = data["number"]
            if number in records or data["nodeid"] != plugin.submitted.get(number):
                raise ValueError("duplicate or mismatched child record")
            records[number] = data
        if set(records) != set(plugin.submitted):
            raise ValueError(f"missing task records: {set(plugin.submitted)-set(records)}")
        if not records or any(row["nodeid"] not in known for row in records.values()):
            raise ValueError("no tasks or unrecognized child test")
        bootstrap = []
        booted = set()
        for path in Path(temp).glob("pre-task-*.jsonl"):
            lines = [json.loads(line) for line in path.read_text().splitlines()]
            if not lines or set(lines[0]) != {"startup"}:
                raise ValueError("incomplete startup trace")
            booted.add(lines[0]["startup"])
            bootstrap.extend(line for line in lines[1:] if set(line) == {"path", "callers"})
            if len(lines[1:]) != len([line for line in lines[1:]
                                      if set(line) == {"path", "callers"}]):
                raise ValueError("invalid pre-task source read")
        if {row["pid"] for row in records.values()} - booted:
            raise ValueError("spawned worker lacked early source-read hook")
        output.write_text(json.dumps({"tasks": len(plugin.submitted),
                                      "callers": sorted(set(plugin.submitted.values())),
                                      "records": [records[i] for i in sorted(records)],
                                      "bootstrap": bootstrap},
                                     sort_keys=True, separators=(",", ":")))
        print(len(records), "complete tasks", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
