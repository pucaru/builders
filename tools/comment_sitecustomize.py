"""Injected as sitecustomize during clean spawned-worker source-read profiling."""
import json
import os
from pathlib import Path
import sys


_directory = os.environ.get("BLAST_COMMENT_POOL_DIR")
_prefix = os.environ.get("BLAST_COMMENT_SOURCE_PREFIX")
if _directory and _prefix:
    _log = Path(_directory) / f"pre-task-{os.getpid()}.jsonl"
    _log.write_text(json.dumps({"startup": os.getpid()}) + "\n")

    def _source_open(event, args):
        if (event != "open" or os.environ.get("BLAST_COMMENT_ACTIVE")
                or not args or not isinstance(args[0], (str, bytes))):
            return
        filename = os.path.abspath(os.fsdecode(args[0]))
        if not (filename.startswith(_prefix) and filename.endswith(".py")):
            return
        frame = sys._getframe(1)
        callers = []
        while frame is not None:
            path = frame.f_code.co_filename
            if "/sqlglot/" in path or "/tests/" in path or "importlib" in path:
                callers.append(path + ":" + str(frame.f_lineno))
            frame = frame.f_back
        with _log.open("a") as stream:
            stream.write(json.dumps({"path": filename[len(_prefix):],
                                     "callers": callers[:5]}) + "\n")

    sys.addaudithook(_source_open)
