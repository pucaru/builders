"""Observe SQLGlot receiver classes on the unmodified pinned test suite.

This map is deliberately broader than an instantiation map: invoking an inherited
method on a subclass credits the test to the subclass and every SQLGlot base.
Use during pytest setup is credited to every test in that test class.
"""
import argparse
import builtins
from collections import defaultdict
import functools
import gzip
import json
import os
from pathlib import Path
import sys

import pytest


class ClassUse:
    def __init__(self, root):
        self.prefix = str(root / "sqlglot") + os.sep
        self.current = ""
        self.phase = ""
        self.used = defaultdict(set)
        self.setup = defaultdict(set)
        self.import_error_classes = set()

    @staticmethod
    def keys(value):
        cls = value if isinstance(value, type) else type(value)
        for base in getattr(cls, "__mro__", ()):
            if base.__module__ == "sqlglot" or base.__module__.startswith("sqlglot."):
                yield base.__module__ + ":" + base.__qualname__

    def record(self, value):
        if not self.current:
            return
        for key in self.keys(value):
            self.used[key].add(self.current)
            if self.phase == "setup":
                self.setup[key].add(self.current.rsplit("::", 1)[0])

    def wrap_constructor(self, base):
        original = base.__dict__.get("__init__")
        if original is None or getattr(original, "_blast_class_profile", False):
            return

        @functools.wraps(original)
        def wrapped(*a, __original=original, **kw):
            self.record(a[0])
            return __original(*a, **kw)

        wrapped._blast_class_profile = True
        setattr(base, "__init__", wrapped)

    def wrap_validation(self, base):
        original = base.__dict__.get("error_messages")
        if original is None or getattr(original, "_blast_import_profile", False):
            return

        @functools.wraps(original)
        def wrapped(*a, __original=original, **kw):
            if not self.current:
                self.import_error_classes.update(self.keys(a[0]))
            return __original(*a, **kw)

        wrapped._blast_import_profile = True
        setattr(base, "error_messages", wrapped)

    def install_early(self):
        """Wrap Expr before any sqlglot module imports and caches instances."""
        original = builtins.__build_class__
        roots = {
            ("sqlglot.dialects.dialect", "Dialect"),
            ("sqlglot.tokens", "Tokenizer"),
            ("sqlglot.parser", "Parser"),
            ("sqlglot.generator", "Generator"),
            ("sqlglot.expressions.core", "Expr"),
            ("sqlglot.expressions.core", "Expression"),
        }

        def build(function, name, *bases, **kwargs):
            result = original(function, name, *bases, **kwargs)
            module = getattr(result, "__module__", "")
            if (module, name) in roots:
                self.wrap_constructor(result)
            if (module, name) in (("sqlglot.expressions.core", "Expr"),
                                  ("sqlglot.expressions.core", "Expression")):
                self.wrap_validation(result)
            return result

        builtins.__build_class__ = build
        return original

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
        self.phase = "setup"  # shared teardown can be changed by a class edit too
        try:
            return (yield)
        finally:
            self.phase = ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("checkout", type=Path)
    ap.add_argument("tests_json", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--import-output", type=Path)
    ap.add_argument("--tests", nargs="+", default=["tests"])
    ap.add_argument("--tb", default="no")
    args = ap.parse_args()
    root = args.checkout.resolve()
    tests_json = args.tests_json.resolve()
    output = args.output.resolve()
    import_output = args.import_output.resolve() if args.import_output is not None else None
    tests = json.loads(tests_json.read_text())["tests"]
    ids = {t["id"] for t in tests}
    by_scope = defaultdict(set)
    for nodeid in ids:
        by_scope[nodeid.rsplit("::", 1)[0]].add(nodeid)
    os.chdir(root)
    sys.path.insert(0, str(root))
    if "sqlglot" in sys.modules:
        raise RuntimeError("SQLGlot was imported before the trace hook")
    plugin = ClassUse(root)
    original_build = plugin.install_early()
    try:
        rc = pytest.main(["-q", *args.tests, "--tb=" + args.tb], plugins=[plugin])
    finally:
        builtins.__build_class__ = original_build
    if rc:
        return rc
    result = {}
    for key, selected in plugin.used.items():
        selected = selected & ids
        for scope in plugin.setup[key]:
            selected.update(by_scope[scope])
        result[key] = sorted(selected)
    payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if output.suffix == ".gz":
        with gzip.GzipFile(output, "wb", mtime=0) as handle:
            handle.write(payload)
    else:
        output.write_bytes(payload)
    if import_output is not None:
        import_output.write_text(json.dumps(sorted(plugin.import_error_classes)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
