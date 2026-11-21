"""Profile numeric escape keys on the unmodified pinned SQLGlot suite."""
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

from numeric_key_child import run_task
from numeric_key_probe import NumericKeyProbe


class NumericProfile:
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
                               function, args, kwargs)

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
    manifest = json.loads(args.tests_json.resolve().read_text())["tests"]
    known = {test["id"] for test in manifest}
    by_scope = defaultdict(set)
    for nodeid in known:
        by_scope[nodeid.rsplit("::", 1)[0]].add(nodeid)
    output = args.output.resolve()
    impact_sha256 = hashlib.sha256(args.impact_map.resolve().read_bytes()).hexdigest()
    os.chdir(root)
    sys.path.insert(0, str(root))
    if "sqlglot" in sys.modules:
        raise RuntimeError("SQLGlot imported before numeric key hook")
    probe = NumericKeyProbe()
    plugin = NumericProfile(probe)
    original = probe.install_early()
    try:
        with tempfile.TemporaryDirectory(prefix="blast-numeric-keys-") as temp:
            os.environ["BLAST_NUMERIC_KEY_DIR"] = temp
            os.environ["PYTHONPATH"] = os.pathsep.join(
                [str(root), str(Path(__file__).resolve().parent)])
            with pytest.MonkeyPatch.context() as monkeypatch:
                plugin.install_pool(monkeypatch)
                result = pytest.main(["-q", *args.tests, "--tb=no"], plugins=[plugin])
            if result:
                return result
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
            for owner, keys in probe.uses.items():
                for key, ids in keys.items():
                    uses[owner][key].update(ids)
            for (owner, key), scopes in probe.setup.items():
                for scope in scopes:
                    uses[owner][key].update(by_scope[scope])
            nested = set()
            for record in records.values():
                if record["nested"]:
                    nested.add(record["nodeid"])
                for owner, keys in record["uses"].items():
                    for key, ids in keys.items():
                        if ids != [record["nodeid"]]:
                            raise ValueError(f"bad child context {record['number']}")
                        uses[owner][key].update(ids)
                        if record["number"] in plugin.submitted_setup:
                            uses[owner][key].update(by_scope[record["nodeid"].rsplit("::", 1)[0]])
            if any(not ids <= known | {""} for keys in uses.values() for ids in keys.values()):
                raise ValueError("unknown test context")
            import_reads = {owner: sorted(key for key, ids in keys.items() if "" in ids)
                            for owner, keys in uses.items()}
            for keys in uses.values():
                for ids in keys.values():
                    ids.discard("")
            caller_tasks = {}
            for nodeid in plugin.submitted.values():
                caller_tasks[nodeid] = caller_tasks.get(nodeid, 0) + 1
            payload = {
                "uses": {owner: {key: sorted(ids) for key, ids in sorted(keys.items())}
                         for owner, keys in sorted(uses.items())},
                "import_reads": import_reads, "nested": sorted(nested),
                "callers": sorted(caller_tasks), "caller_tasks": caller_tasks,
                "tasks": len(plugin.submitted), "impact_sha256": impact_sha256,
            }
            data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
            with gzip.GzipFile(output, "wb", mtime=0) as stream:
                stream.write(data)
            print(f"{len(known)} tests, {len(plugin.submitted)} child tasks, "
                  f"{len(uses)} owner classes, {len(nested)} nested", flush=True)
    finally:
        builtins.__build_class__ = original
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
