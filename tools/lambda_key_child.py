"""Picklable process-pool wrapper for exact parser lambda calls."""
import json
import os
from pathlib import Path
import sys
import threading


_root = Path(os.environ.get("BLAST_LAMBDA_KEY_ROOT", "/nonexistent"))
_prefix = str(_root / "sqlglot") + os.sep


def run_task(number, nodeid, function, args, kwargs):
    calls = set()

    def profile(frame, event, arg):
        if event != "call":
            return
        code = frame.f_code
        if code.co_name != "<lambda>" or not code.co_filename.startswith(_prefix):
            return
        path = Path(code.co_filename).relative_to(_root).as_posix()
        if path.startswith("sqlglot/parsers/"):
            calls.add((path, code.co_firstlineno, code.co_qualname))

    old = sys.getprofile()
    sys.setprofile(profile)
    threading.setprofile(profile)
    try:
        return function(*args, **kwargs)
    finally:
        sys.setprofile(old)
        threading.setprofile(None)
        target = Path(os.environ["BLAST_LAMBDA_KEY_DIR"]) / f"task-{number}.json"
        target.write_text(json.dumps({"number": number, "nodeid": nodeid,
                                      "pid": os.getpid(), "calls": sorted(calls)}))
