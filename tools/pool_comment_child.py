"""Trace direct SQLGlot source reads in each pristine process-pool task."""
import json
import os
from pathlib import Path
import sys


_active = None
_reads = set()
_installed = False


def _audit(event, args):
    if _active is None or event != "open" or not args or not isinstance(args[0], (str, bytes)):
        return
    filename = os.path.abspath(os.fsdecode(args[0]))
    prefix = os.environ["BLAST_COMMENT_SOURCE_PREFIX"]
    if not (filename.startswith(prefix) and filename.endswith(".py")):
        return
    frame = sys._getframe(1)
    callers = []
    while frame is not None:
        path = frame.f_code.co_filename
        if "/sqlglot/" in path or "/tests/" in path or "importlib" in path:
            callers.append(path + ":" + str(frame.f_lineno))
        frame = frame.f_back
    _reads.add((filename[len(prefix):], tuple(callers[:5])))


def run_task(number, nodeid, function, args, kwargs):
    global _active, _installed
    if not _installed:
        sys.addaudithook(_audit)
        _installed = True
    _active = nodeid
    os.environ["BLAST_COMMENT_ACTIVE"] = nodeid
    _reads.clear()
    try:
        return function(*args, **kwargs)
    finally:
        destination = Path(os.environ["BLAST_COMMENT_POOL_DIR"]) / f"{number}.json"
        destination.write_text(json.dumps({"number": number, "nodeid": nodeid,
                                           "pid": os.getpid(),
                                           "reads": sorted((path, list(callers))
                                                           for path, callers in _reads)}))
        _active = None
        os.environ.pop("BLAST_COMMENT_ACTIVE", None)
