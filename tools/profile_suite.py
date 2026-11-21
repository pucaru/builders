"""Trace the clean checkout with one context per test, including setup/teardown."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
import os
from pathlib import Path
import sys
import tempfile

from profile_child import run_task

import coverage
import pytest


class Profile:
    def __init__(self, trace):
        self.trace = trace
        self.current = ""
        self.subprocess = set()
        self.pool_tests = set()
        sys.addaudithook(self.audit)

    def instrument_pools(self, monkeypatch):
        submit = ProcessPoolExecutor.submit

        def submit_with_context(pool, function, /, *args, **kwargs):
            self.pool_tests.add(self.current)
            return submit(pool, run_task, self.current, function, args, kwargs)

        monkeypatch.setattr(ProcessPoolExecutor, "submit", submit_with_context)

    def audit(self, event, args):
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork"}:
            self.subprocess.add(self.current)

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_protocol(self, item):
        self.current = item.nodeid
        self.trace.switch_context(self.current)
        try:
            return (yield)
        finally:
            self.current = ""
            self.trace.switch_context("")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tests", nargs="+", default=["tests"])
    parser.add_argument("--with-pools", action="store_true")
    args = parser.parse_args()
    checkout, output = args.checkout.resolve(), args.output.resolve()
    os.chdir(checkout)
    sys.path.insert(0, str(checkout))
    os.environ["PYTHONPATH"] = os.pathsep.join([str(checkout),
                                                 str(Path(__file__).resolve().parent)])
    trace = coverage.Coverage(config_file=False, data_file=None, source=["sqlglot", "tests"])
    plugin = Profile(trace)
    with tempfile.TemporaryDirectory(prefix="blast-coverage-") as directory:
        child_data = str(Path(directory) / ".coverage")
        os.environ["BLAST_CHILD_COVERAGE"] = child_data
        with pytest.MonkeyPatch.context() as monkeypatch, trace.collect():
            if args.with_pools:
                plugin.instrument_pools(monkeypatch)
            result = pytest.main(["-q", *args.tests], plugins=[plugin])
        data = trace.get_data()
        for path in Path(directory).glob(".coverage.*"):
            child = coverage.CoverageData(basename=str(path))
            child.read()
            data.update(child)
    if result:
        return result
    lines = {}
    for name in sorted(data.measured_files()):
        path = Path(name).relative_to(checkout).as_posix()
        lines[path] = dict(sorted(data.contexts_by_lineno(name).items()))
    with gzip.GzipFile(output, "wb", mtime=0) as handle:
        handle.write(json.dumps({"lines": lines, "subprocess": sorted(plugin.subprocess),
                                 "pools": sorted(plugin.pool_tests)},
                                sort_keys=True, separators=(",", ":")).encode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
