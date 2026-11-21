"""Select tests and minimize the official simulated scheduling cost."""
import argparse
import heapq
import json
from pathlib import Path

from impact import Impact


def schedule(tests):
    jobs = sorted(((round(test["seconds"] * 1000), test["number"]) for test in tests),
                  key=lambda job: (-job[0], job[1]))
    if not jobs:
        return []
    best_cost = float("inf")
    best = []
    total = sum(duration for duration, _ in jobs)
    for count in range(1, min(8, len(jobs)) + 1):
        overhead = count * 2000
        if max(jobs[0][0], (total + count - 1) // count) + overhead >= best_cost:
            continue
        workers = [[] for _ in range(count)]
        queue = [(0, index) for index in range(count)]
        for duration, test in jobs:
            load, index = queue[0]
            workers[index].append(test)
            heapq.heapreplace(queue, (load + duration, index))
        cost = max(load for load, _ in queue) + overhead
        if cost < best_cost:
            best_cost, best = cost, workers
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("/data"))
    parser.add_argument("--mode", choices=["all", "static", "file", "function", "hybrid",
                                                   "pool-file", "pool-function", "pool-noop"],
                        default="pool-noop")
    parser.add_argument("--map", type=Path, default=Path(__file__).with_name("impact.json.gz"))
    args = parser.parse_args()
    tests = json.loads((args.data / "tests.json").read_text())["tests"]
    impact = None if args.mode == "all" else Impact(tests, args.map, args.mode)
    plans = {}
    for patch in sorted((args.data / "commits").glob("*.patch")):
        selection = tests if impact is None else impact.select(
            patch.read_text(encoding="utf-8", errors="surrogateescape"))
        key = tuple(test["number"] for test in selection)
        if key not in plans:
            plans[key] = schedule(selection)
        workers = plans[key]
        print(json.dumps({"commit": patch.stem, "workers": workers}, separators=(",", ":")))


if __name__ == "__main__":
    main()
