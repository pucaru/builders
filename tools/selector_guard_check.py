"""Check that observable headers and mixed comment/code edits fail closed."""
import difflib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact import Impact, replacement_statements, sections, apply_hunks


def patch_for(path, source, patched):
    diff = difflib.unified_diff(source.splitlines(keepends=True),
                                patched.splitlines(keepends=True),
                                f"a/{path}", f"b/{path}")
    return f"diff --git a/{path} b/{path}\n" + "".join(diff)


def main():
    manifest = Path(sys.argv[1])
    map_path = Path(sys.argv[2])
    tests = json.loads(manifest.read_text())["tests"]
    impact = Impact(tests, map_path, "pool-noop")
    path = "sqlglot/helper.py"
    original = impact.sources[path]
    anchor = "    return int(number)\n"
    assert original.count(anchor) == 1
    body = original.replace(anchor, "    return 0\n", 1)

    header = "# coding: utf-8\n" + body
    assert impact.select_ids(patch_for(path, original, header)) == impact.all_ids

    mixed = body.replace("    return 0\n", "    return 0  # changed text\n", 1)
    assert impact.select_ids(patch_for(path, original, mixed)) == impact.all_ids

    relocated = Path(sys.argv[3]).read_text()
    _, _, hunk = sections(relocated)[0]
    source = impact.sources["sqlglot/generator.py"]
    assert replacement_statements(source, apply_hunks(source, hunk), hunk) is None
    print("header, mixed-comment, and relocation guards passed")


if __name__ == "__main__":
    main()
