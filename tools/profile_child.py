"""Carry the active pytest node into SQLGlot's persistent worker processes."""
import os
from multiprocessing.util import Finalize

import coverage

_trace = None


def _save():
    _trace.stop()
    _trace.save()


def run_task(nodeid, function, args, kwargs):
    global _trace
    if _trace is None:
        _trace = coverage.Coverage(config_file=False, source=["sqlglot", "tests"],
                                   data_file=os.environ["BLAST_CHILD_COVERAGE"],
                                   data_suffix=True)
        _trace.start()
        Finalize(None, _save, exitpriority=1)
    _trace.switch_context(nodeid)
    return function(*args, **kwargs)
