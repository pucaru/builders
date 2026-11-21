"""Trace immutable Dialect class-field reads on unmodified pinned SQLGlot."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import builtins
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import pytest

from scalar_read_child import run_task
from scalar_read_probe import ScalarReadProbe, scalar_names


class ScalarProfile:
    def __init__(self, probe):
        self.probe = probe
        self.submitted = {}
        self.submitted_setup = set()
        self.submit = ProcessPoolExecutor.submit

    def install_pool(self, monkeypatch):
        def submit_with_test(pool, function, /, *args, **kwargs):
            number = len(self.submitted)
            self.submitted[number] = self.probe.current
            if self.probe.phase == "setup":
                self.submitted_setup.add(number)
            return self.submit(pool, run_task, number, self.probe.current,
                               sorted(self.probe.names), function, args, kwargs)

        monkeypatch.setattr(ProcessPoolExecutor, "submit", submit_with_test)

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_protocol(self, item):
        self.probe.current = item.nodeid
        try:
            return (yield)
        finally:
            self.probe.current = ""

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_setup(self, item):
        self.probe.phase = "setup"
        try:
            return (yield)
        finally:
            self.probe.phase = ""

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_teardown(self, item, nextitem):
        self.probe.phase = "setup"
        try:
            return (yield)
        finally:
            self.probe.phase = ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    parser.add_argument("tests_json", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--impact-map", type=Path, default=Path("impact.json.gz"))
    parser.add_argument("--tests", nargs="+", default=["tests"])
    args = parser.parse_args()
    root = args.checkout.resolve()
    known = {test["id"] for test in json.loads(args.tests_json.resolve().read_text())["tests"]}
    by_scope = defaultdict(set)
    for nodeid in known:
        by_scope[nodeid.rsplit("::", 1)[0]].add(nodeid)
    output = args.output.resolve()
    digest = hashlib.sha256(args.impact_map.resolve().read_bytes()).hexdigest()
    names = scalar_names(root)
    os.chdir(root)
    sys.path.insert(0, str(root))
    if "sqlglot" in sys.modules:
        raise RuntimeError("SQLGlot imported before dialect read hook")
    probe = ScalarReadProbe(names)
    plugin = ScalarProfile(probe)
    original = probe.install_early()
    try:
        with tempfile.TemporaryDirectory(prefix="blast-scalar-reads-") as temp:
            os.environ["BLAST_SCALAR_READ_DIR"] = temp
            os.environ["PYTHONPATH"] = os.pathsep.join(
                [str(root), str(Path(__file__).resolve().parent)])
            with pytest.MonkeyPatch.context() as monkeypatch:
                plugin.install_pool(monkeypatch)
                rc = pytest.main(["-q", *args.tests, "--tb=no"], plugins=[plugin])
            if rc:
                return rc
            records = {}
            for path in Path(temp).glob("*.json"):
                record = json.loads(path.read_text())
                number = record["number"]
                if number in records or record["nodeid"] != plugin.submitted.get(number):
                    raise ValueError(f"bad child record {path}")
                records[number] = record
            if set(records) != set(plugin.submitted):
                raise ValueError(f"missing child tasks: {set(plugin.submitted) - set(records)}")
            uses = defaultdict(lambda: defaultdict(set))
            for owner, fields in probe.uses.items():
                for name, ids in fields.items():
                    uses[owner][name].update(ids)
            for (owner, name), scopes in probe.setup.items():
                for scope in scopes:
                    uses[owner][name].update(by_scope[scope])
            nested = set()
            for record in records.values():
                if record["nested"]:
                    nested.add(record["nodeid"])
                for owner, fields in record["uses"].items():
                    for name, ids in fields.items():
                        if ids != [record["nodeid"]]:
                            raise ValueError(f"bad child context {record['number']}")
                        uses[owner][name].update(ids)
                        if record["number"] in plugin.submitted_setup:
                            uses[owner][name].update(by_scope[record["nodeid"].rsplit("::", 1)[0]])
            if any(not ids <= known | {""} for fields in uses.values() for ids in fields.values()):
                raise ValueError("unknown test context")
            imported = {owner: sorted(name for name, ids in fields.items() if "" in ids)
                        for owner, fields in uses.items()}
            shared = defaultdict(set)
            for (owner, name), scopes in probe.setup.items():
                if scopes:
                    shared[owner].add(name)
            for record in records.values():
                if record["number"] in plugin.submitted_setup:
                    for owner, fields in record["uses"].items():
                        shared[owner].update(fields)
            for fields in uses.values():
                for ids in fields.values():
                    ids.discard("")
            counts = {}
            for nodeid in plugin.submitted.values():
                counts[nodeid] = counts.get(nodeid, 0) + 1
            payload = {"uses": {owner: {name: sorted(ids) for name, ids in sorted(fields.items())}
                                for owner, fields in sorted(uses.items())},
                       "import_reads": imported,
                       "shared_reads": {owner: sorted(fields) for owner, fields in sorted(shared.items())},
                       "names": sorted(names),
                       "nested": sorted(nested), "callers": sorted(counts),
                       "caller_tasks": counts, "tasks": len(plugin.submitted),
                       "impact_sha256": digest}
            with gzip.GzipFile(output, "wb", mtime=0) as stream:
                stream.write((json.dumps(payload, sort_keys=True, separators=(",", ":"))
                              + "\n").encode())
            print(f"{len(known)} test manifest, {len(plugin.submitted)} child tasks, "
                  f"{len(names)} field names, {len(uses)} owner keys", flush=True)
    finally:
        builtins.__build_class__ = original
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
