"""A picklable wrapper for recording SQLGlot classes inside pool workers."""
import functools
import json
import os
from pathlib import Path
import sys

_active = None
_classes = set()
_nested = False
_installed = False


def _audit(event, _args):
    global _nested
    if _active is not None and event in {"subprocess.Popen", "os.fork", "os.posix_spawn"}:
        _nested = True


def _install():
    global _installed
    if _installed:
        return
    from sqlglot.dialects.dialect import Dialect
    from sqlglot.expressions.core import Expr, Expression
    from sqlglot.generator import Generator
    from sqlglot.parser import Parser
    from sqlglot.tokens import Tokenizer

    for base in (Dialect, Tokenizer, Parser, Generator, Expr, Expression):
        original = base.__dict__.get("__init__")
        if original is None:
            continue

        @functools.wraps(original)
        def constructor(self, *args, __original=original, **kwargs):
            if _active is not None:
                for cls in type(self).__mro__:
                    if cls.__module__ == "sqlglot" or cls.__module__.startswith("sqlglot."):
                        _classes.add(cls.__module__ + ":" + cls.__qualname__)
            return __original(self, *args, **kwargs)

        base.__init__ = constructor
    sys.addaudithook(_audit)
    _installed = True


def run_task(number, nodeid, function, args, kwargs):
    global _active, _nested
    _install()
    _active = nodeid
    _classes.clear()
    _nested = False
    try:
        return function(*args, **kwargs)
    finally:
        path = Path(os.environ["BLAST_POOL_CLASS_DIR"]) / f"{number}.json"
        path.write_text(json.dumps({"number": number, "nodeid": nodeid,
                                    "classes": sorted(_classes), "nested": _nested}))
        _active = None
