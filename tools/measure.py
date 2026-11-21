"""Run a selector with input-only data and score its output outside the selector."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("selector", type=Path)
    parser.add_argument("scorer", type=Path)
    parser.add_argument("data", type=Path)
    parser.add_argument("labels", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode")
    args = parser.parse_args()
    command = [sys.executable, str(args.selector), "--data", str(args.data)]
    if args.mode:
        command.extend(["--mode", args.mode])
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    with args.output.open("wb") as stream:
        subprocess.run(command, check=True, stdout=stream, timeout=180)
    wall = time.monotonic() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime)
    if args.output.stat().st_size > 2_000_000:
        raise ValueError("selector output exceeded 2 MB")
    print(f"host wall={wall:.3f}s cpu={cpu:.3f}s", flush=True)
    subprocess.run([sys.executable, str(args.scorer), str(args.data), str(args.labels),
                    str(args.output)], check=True)
    truth = json.loads(args.labels.read_text())["commits"]
    for line in args.output.read_text().splitlines():
        row = json.loads(line)
        name = row["commit"]
        expected = set(truth[name]["failing"])
        selected = {test for worker in row["workers"] for test in worker}
        if missing := expected - selected:
            print(f"{name}: missed {len(missing)}/{len(expected)} failing tests")


if __name__ == "__main__":
    main()
