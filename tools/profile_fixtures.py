"""Record which numbered tests read each fixture in the pristine checkout."""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sys

import pytest


class FixtureReads:
    def __init__(self, root):
        self.root = str(root)
        self.prefix = self.root + "/tests/fixtures/"
        self.active = ""
        self.reads = defaultdict(set)
        self.shared = defaultdict(set)
        sys.addaudithook(self.audit)

    def audit(self, event, args):
        if event != "open":
            return
        path = args[0]
        if isinstance(path, str) and path.startswith(self.prefix):
            name = path[len(self.root) + 1:]
            self.reads[name].add(self.active)
            frame = sys._getframe(1)
            while frame:
                if frame.f_code.co_name == "setUpClass" and self.active:
                    self.shared[name].add(self.active.rsplit("::", 1)[0])
                    break
                if frame.f_code.co_name == "setUpModule" and self.active:
                    self.shared[name].add(self.active.split("::", 1)[0])
                    break
                frame = frame.f_back

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_protocol(self, item):
        self.active = item.nodeid
        try:
            return (yield)
        finally:
            self.active = ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--shared", type=Path)
    args = parser.parse_args()
    root, output = args.checkout.resolve(), args.output.resolve()
    shared_output = args.shared.resolve() if args.shared else None
    os.chdir(root)
    sys.path.insert(0, str(root))
    reads = FixtureReads(root)
    result = pytest.main(["-q", "tests", "--tb=no"], plugins=[reads])
    if not result:
        output.write_text(json.dumps(
            {p: sorted(ids) for p, ids in sorted(reads.reads.items())},
            separators=(",", ":"),
        ) + "\n")
        if shared_output:
            shared_output.write_text(json.dumps(
                {p: sorted(ids) for p, ids in sorted(reads.shared.items())},
                separators=(",", ":"),
            ) + "\n")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
