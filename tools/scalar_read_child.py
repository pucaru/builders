"""Picklable pool task wrapper for dialect scalar read observations."""
import json
import os
from pathlib import Path
import sys

from scalar_read_probe import ScalarReadProbe

_probe = None
_nested = False


def _audit(event, _args):
    global _nested
    if _probe is not None and _probe.current and event in {
            "subprocess.Popen", "os.fork", "os.posix_spawn"}:
        _nested = True


def run_task(number, nodeid, fields, function, args, kwargs):
    global _probe, _nested
    if _probe is None:
        _probe = ScalarReadProbe(set(fields))
        _probe.install_direct()
        sys.addaudithook(_audit)
    _probe.current = nodeid
    _probe.uses.clear()
    _nested = False
    try:
        return function(*args, **kwargs)
    finally:
        path = Path(os.environ["BLAST_SCALAR_READ_DIR"]) / f"{number}.json"
        path.write_text(json.dumps({"number": number, "nodeid": nodeid,
                                    "uses": _probe.payload(), "nested": _nested}))
        _probe.current = ""
