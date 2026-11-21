"""Picklable process-pool task wrapper for numeric escape key observations."""
import json
import os
from pathlib import Path
import sys

from numeric_key_probe import NumericKeyProbe

_probe = NumericKeyProbe()
_installed = False
_nested = False


def _audit(event, _args):
    global _nested
    if _probe.current and event in {"subprocess.Popen", "os.fork", "os.posix_spawn"}:
        _nested = True


def run_task(number, nodeid, function, args, kwargs):
    global _installed, _nested
    if not _installed:
        _probe.install_direct()
        sys.addaudithook(_audit)
        _installed = True
    _probe.current = nodeid
    _probe.uses.clear()
    _nested = False
    try:
        return function(*args, **kwargs)
    finally:
        path = Path(os.environ["BLAST_NUMERIC_KEY_DIR"]) / f"{number}.json"
        path.write_text(json.dumps({"number": number, "nodeid": nodeid,
                                    "uses": _probe.payload(), "nested": _nested}))
        _probe.current = ""
