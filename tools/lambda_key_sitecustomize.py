"""Start a parser lambda call trace before spawn deserialization and imports."""
import json
import os
from pathlib import Path
import sys


_directory = os.environ.get("BLAST_LAMBDA_KEY_DIR")
_root = os.environ.get("BLAST_LAMBDA_KEY_ROOT")
if _directory and _root:
    _root_path = Path(_root)
    _prefix = str(_root_path / "sqlglot") + os.sep
    _log = Path(_directory) / f"startup-{os.getpid()}.jsonl"
    _log.write_text(json.dumps({"startup": os.getpid()}) + "\n")

    def _profile(frame, event, arg):
        if event != "call":
            return
        code = frame.f_code
        if code.co_name != "<lambda>" or not code.co_filename.startswith(_prefix):
            return
        path = Path(code.co_filename).relative_to(_root_path).as_posix()
        if path.startswith("sqlglot/parsers/"):
            with _log.open("a") as stream:
                stream.write(json.dumps({"key": [path, code.co_firstlineno,
                                                   code.co_qualname]}) + "\n")

    sys.setprofile(_profile)
