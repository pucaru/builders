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
        sys.addaudithook(self.audit)

    def audit(self, event, args):
        if event != "open":
            return
        path = args[0]
        if isinstance(path, str) and path.startswith(self.prefix):
            self.reads[path[len(self.root) + 1:]].add(self.active)

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
    args = parser.parse_args()
    root, output = args.checkout.resolve(), args.output.resolve()
    os.chdir(root)
    sys.path.insert(0, str(root))
    reads = FixtureReads(root)
    result = pytest.main(["-q", "tests", "--tb=no"], plugins=[reads])
    if not result:
        output.write_text(json.dumps(
            {p: sorted(ids) for p, ids in sorted(reads.reads.items())},
            separators=(",", ":"),
        ) + "\n")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
