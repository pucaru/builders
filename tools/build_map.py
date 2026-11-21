"""Build import, fixture and coverage maps from pristine SQLGlot."""
import argparse
import ast
from collections import defaultdict
import gzip
import importlib.util
import json
from pathlib import Path
from tokenize import open as source_open


def module_name(path):
    name = path.removesuffix(".py").replace("/", ".")
    return name.removesuffix(".__init__")


def add_module(target, modules, edges):
    parts = target.split(".")
    for length in range(1, len(parts) + 1):
        if path := modules.get(".".join(parts[:length])):
            edges.add(path)


def build(root, profile):
    sources = {}
    for folder in ("sqlglot", "tests"):
        for path in sorted((root / folder).rglob("*.py")):
            with source_open(path) as handle:
                sources[path.relative_to(root).as_posix()] = handle.read()
    modules = {module_name(path): path for path in sources}
    dialects = {name.rsplit(".", 1)[1]: path for name, path in modules.items()
                if name.startswith("sqlglot.dialects.") and name.count(".") == 2}
    fixtures = [path.relative_to(root).as_posix() for path in
                sorted((root / "tests" / "fixtures").rglob("*")) if path.is_file()]
    graph = defaultdict(set)
    source_readers = set()
    for path, source in sources.items():
        module = module_name(path)
        package = module if path.endswith("/__init__.py") else module.rpartition(".")[0]
        strings = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    add_module(alias.name, modules, graph[path])
            elif isinstance(node, ast.ImportFrom):
                target = importlib.util.resolve_name("." * node.level + (node.module or ""),
                                                     package) if node.level else node.module
                add_module(target, modules, graph[path])
                for alias in node.names:
                    add_module(f"{target}.{alias.name}", modules, graph[path])
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.add(node.value.lower())
            elif path.startswith("tests/") and isinstance(node, ast.Attribute):
                if node.attr in {"getsource", "read_text", "read_bytes", "source_from_cache"}:
                    source_readers.add(path)
        graph[path].update(dialects[name] for name in strings & dialects.keys())
        if path.startswith("tests/"):
            for fixture in fixtures:
                if any(part.lower() in strings for part in (Path(fixture).name, Path(fixture).stem)):
                    graph[path].add(fixture)

    reverse = defaultdict(list)
    for path in sources:
        if not path.startswith("tests/"):
            continue
        visited, pending = set(), [path]
        while pending:
            item = pending.pop()
            if item not in visited:
                visited.add(item)
                pending.extend(graph[item] - visited)
        for item in visited:
            reverse[item].append(path)

    line_map = {}
    context_sets = []
    set_index = {}
    for path, lines in profile.get("lines", {}).items():
        packed = {}
        for line, contexts in lines.items():
            key = tuple(sorted(contexts))
            if key not in set_index:
                set_index[key] = len(context_sets)
                context_sets.append(key)
            packed[line] = set_index[key]
        line_map[path] = packed
    return {"sources": sources, "fixtures": fixtures, "static": reverse,
            "source_readers": sorted(source_readers), "lines": line_map,
            "contexts": context_sets, "subprocess": profile.get("subprocess", [])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--profile", type=Path, action="append", default=[])
    args = parser.parse_args()
    profile = {"lines": {}, "subprocess": set()}
    for path in args.profile:
        with gzip.open(path, "rt") as handle:
            fragment = json.load(handle)
        profile["subprocess"].update(fragment["subprocess"])
        for source, lines in fragment["lines"].items():
            merged = profile["lines"].setdefault(source, {})
            for line, contexts in lines.items():
                merged[line] = sorted(set(merged.get(line, [])) | set(contexts))
    profile["subprocess"] = sorted(profile["subprocess"])
    result = build(args.checkout, profile)
    with gzip.GzipFile(args.output, "wb", mtime=0) as handle:
        handle.write(json.dumps(result, sort_keys=True, separators=(",", ":")).encode())


if __name__ == "__main__":
    main()
