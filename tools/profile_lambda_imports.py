"""Observe parser lambda calls outside pytest tests on pristine SQLGlot."""
import argparse
import importlib
import hashlib
import json
import os
from pathlib import Path
import pkgutil
import sys
import threading

import pytest


class TestContexts:
    def __init__(self):
        self.current = ""
        self.phase = ""

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
    ap.add_argument("output", type=Path)
    ap.add_argument("--impact-map", type=Path)
    ap.add_argument("--merge", type=Path)
    ap.add_argument("--sweep-imports", action="store_true")
    args = ap.parse_args()
    root = args.checkout.resolve()
    output = args.output.resolve()
    impact_map = (args.impact_map.resolve() if args.impact_map is not None
                  else output.with_name("impact.json.gz"))
    os.chdir(root)
    sys.path.insert(0, str(root))
    if "sqlglot" in sys.modules:
        raise RuntimeError("SQLGlot imported before lambda call profile")
    plugin = TestContexts()
    seen = set()
    shared = set()
    prefix = str(root / "sqlglot") + os.sep

    def profile(frame, event, arg):
        if event != "call":
            return
        code = frame.f_code
        if code.co_name != "<lambda>" or not code.co_filename.startswith(prefix):
            return
        path = Path(code.co_filename).relative_to(root).as_posix()
        if path.startswith("sqlglot/parsers/"):
            key = (path, code.co_firstlineno, code.co_qualname)
            if not plugin.current:
                seen.add(key)
            elif plugin.phase in {"setup", "teardown"}:
                shared.add(key)

    previous = sys.getprofile()
    sys.setprofile(profile)
    threading.setprofile(profile)
    try:
        if args.sweep_imports:
            package = importlib.import_module("sqlglot")
            for module in pkgutil.walk_packages(package.__path__, "sqlglot."):
                if module.name != "sqlglot.__main__":
                    importlib.import_module(module.name)
            rc = 0
        else:
            rc = pytest.main(["-q", "tests", "--tb=no"], plugins=[plugin])
    finally:
        sys.setprofile(previous)
        threading.setprofile(None)
    if rc:
        return rc
    digest = hashlib.sha256(impact_map.read_bytes()).hexdigest()
    if args.merge:
        other = json.loads(args.merge.read_text())
        if other.get("impact_sha256") != digest:
            raise ValueError("merge import map does not match impact map")
        seen.update(tuple(row) for row in other["calls"])
        shared.update(tuple(row) for row in other.get("shared_calls", ()))
    payload = {"impact_sha256": digest, "calls": sorted(seen),
               "shared_calls": sorted(shared)}
    output.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"{len(seen)} parser lambda code objects called outside pytest contexts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
