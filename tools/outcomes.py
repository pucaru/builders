"""Record pytest failure events, including subtests and failed collection."""
import json
import os
from pathlib import Path

failed = set()
collection_errors = set()
collected = set()


def pytest_collection_finish(session):
    collected.update(item.nodeid for item in session.items)


def pytest_collectreport(report):
    if report.failed:
        collection_errors.add(report.nodeid)


def pytest_runtest_logreport(report):
    if report.failed:
        failed.add(report.nodeid)


def pytest_sessionfinish(session, exitstatus):
    Path(os.environ["BLAST_OUTCOMES"]).write_text(json.dumps({
        "failed": sorted(failed), "collection_errors": sorted(collection_errors),
        "collected": sorted(collected),
    }))
