"""Audit direct reads of pinned SQLGlot source during the clean full suite.

This exploratory profile is not included in the selector image. It records
the caller as well as the observed pytest context so that import machinery
and collection-time reads can be reviewed separately.
"""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sys

import pytest


class SourceReads:
    def __init__(self, root):
        self.prefix = str(root / "sqlglot") + os.sep
        self.current = ""
        self.collected = set()
        self.reads = defaultdict(set)
        sys.addaudithook(self.audit)

    def audit(self, event, args):
        if event != "open" or not args or not isinstance(args[0], (str, bytes)):
            return
        filename = os.path.abspath(os.fsdecode(args[0]))
        if not (filename.startswith(self.prefix) and filename.endswith(".py")):
            return
        frame = sys._getframe(1)
        callers = []
        while frame is not None:
            path = frame.f_code.co_filename
            if "/sqlglot/" in path or "/tests/" in path or "importlib" in path:
                callers.append(path + ":" + str(frame.f_lineno))
            frame = frame.f_back
        self.reads[filename[len(self.prefix):]].add((self.current, tuple(callers[:5])))

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_protocol(self, item):
        self.current = item.nodeid
        try:
            return (yield)
        finally:
            self.current = ""

    def pytest_collection_finish(self, session):
        self.collected.update(item.nodeid for item in session.items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("checkout", type=Path)
    ap.add_argument("tests_json", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    root = args.checkout.resolve()
    manifest = json.loads(args.tests_json.read_text())
    expected = {test["id"] for test in manifest["tests"]} | set(manifest["skipped"])
    output = args.output.resolve()
    os.chdir(root)
    sys.path.insert(0, str(root))
    plugin = SourceReads(root)
    rc = pytest.main(["-q", "tests", "--tb=no"], plugins=[plugin])
    if rc or plugin.collected != expected:
        raise RuntimeError(f"clean full suite failed or collected {len(plugin.collected)} / {len(expected)}")
    output.write_text(json.dumps({"collected": sorted(plugin.collected),
                                  "reads": {path: sorted((context, list(callers))
                                                         for context, callers in rows)
                                            for path, rows in sorted(plugin.reads.items())}},
                                 indent=2, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
