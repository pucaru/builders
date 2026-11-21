"""Index pinned source references once instead of scanning them per patch.

The index holds observed tests and test-file paths for names in the unmodified
SQLGlot checkout. It never sees a patch or failure labels.
"""
from collections import defaultdict
import ast
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent


def direct(node):
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        yield node.id
    elif isinstance(node, ast.Attribute):
        yield node.attr
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node.value


def mentioned(node):
    return {name for child in ast.walk(node) for name in direct(child)}


def import_mentions(body):
    names = set()
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.update(*(mentioned(part) for part in (
                *node.decorator_list, *node.args.defaults, *node.args.kw_defaults)
                if part is not None))
        elif isinstance(node, ast.ClassDef):
            names.update(*(mentioned(part) for part in (
                *node.bases, *node.keywords, *node.decorator_list)))
            names.update(import_mentions(node.body))
        else:
            names.update(mentioned(node))
    return names


def main():
    map_path = ROOT / "impact.json.gz"
    with gzip.open(map_path, "rt") as handle:
        maps = json.load(handle)
    trees = {path: ast.parse(source) for path, source in maps["sources"].items()}
    candidates = set()
    for tree in trees.values():
        for owner in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            for stmt in owner.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                    target = stmt.targets[0]
                elif isinstance(stmt, ast.AnnAssign):
                    target = stmt.target
                else:
                    continue
                if isinstance(target, ast.Name):
                    candidates.add(target.id)
        candidates.update(node.attr for node in ast.walk(tree)
                          if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store))
    ids = defaultdict(set)
    files = defaultdict(set)
    imports = set()
    for path, source in maps["sources"].items():
        tree = trees[path]
        contexts = maps["lines"].get(path, {})
        for name in import_mentions(tree.body):
            if name in candidates and name in source:
                imports.add(name)
        for node in ast.walk(tree):
            for name in direct(node):
                if name not in candidates or name not in source:
                    continue
                if hasattr(node, "lineno"):
                    index = contexts.get(str(node.lineno))
                    if index is not None:
                        group = set(maps["contexts"][index])
                        if "" in group:
                            imports.add(name)
                        ids[name].update(group - {""})
                if path.startswith("tests/"):
                    files[name].add(path)
    result = {name: [sorted(ids[name]), sorted(files[name]), name in imports]
              for name in ids.keys() | files.keys() | imports}
    output = ROOT / "reference-index.json.gz"
    data = {"impact_sha256": hashlib.sha256(map_path.read_bytes()).hexdigest(),
            "references": result}
    with gzip.GzipFile(output, "wb", mtime=0) as handle:
        handle.write(json.dumps(data, sort_keys=True, separators=(",", ":")).encode())
    print(f"{len(result)} source symbols, {output.stat().st_size} compressed bytes")


if __name__ == "__main__":
    main()
