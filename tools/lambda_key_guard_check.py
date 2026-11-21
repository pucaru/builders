"""Check that unsupported lambda shapes retain the earlier broad selection."""
import difflib
import gzip
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from impact import Impact


def patch_for(path, before, after):
    return f"diff --git a/{path} b/{path}\n" + "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        f"a/{path}", f"b/{path}"))


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(Path(sys.argv[1]).read_text())["tests"]
    impact = Impact(manifest, root / "impact.json.gz", "pool-noop")
    assert impact.lambda_call_uses is not None
    path = "sqlglot/parsers/dremio.py"
    original = impact.sources[path]
    anchor = "this=seq_get(args, 0),"
    assert original.count(anchor) == 1
    changed = original.replace(anchor, "this=seq_get(args, 1),", 1)
    patch = patch_for(path, original, changed)
    fast = impact.select_ids(patch)
    impact.lambda_call_uses = None
    broad = impact.select_ids(patch)
    assert fast < broad and len(fast) < len(broad)

    # With a valid map, changed closure/scope shapes still use old readers.
    impact = Impact(manifest, root / "impact.json.gz", "pool-noop")
    for expression in ("unknown(args, 0),", "super(),", "__class__,",
                       "(x for x in args),"):
        other = original.replace(anchor, "this=" + expression, 1)
        candidate = patch_for(path, original, other)
        selected = impact.select_ids(candidate)
        impact.lambda_call_uses = None
        expected = impact.select_ids(candidate)
        assert selected == expected, expression
        impact = Impact(manifest, root / "impact.json.gz", "pool-noop")

    target = (path, 110, "DremioParser.<lambda>")
    impact.lambda_import_uses.add(target)
    assert impact.select_ids(patch) == impact.all_ids
    impact.lambda_import_uses.remove(target)
    impact.lambda_shared_uses.add(target)
    assert impact.select_ids(patch) == impact.all_ids

    # A stale or missing map returns to the exact prior selection.
    with tempfile.TemporaryDirectory(prefix="lambda-key-guard-") as temp:
        directory = Path(temp)
        for source in root.iterdir():
            if source.name.endswith((".json", ".json.gz")):
                shutil.copyfile(source, directory / source.name)
        stale = directory / "parser-lambda-key-calls.json.gz"
        content = json.loads(gzip.decompress(stale.read_bytes()))
        content["impact_sha256"] = "0" * 64
        stale.write_bytes(gzip.compress(json.dumps(content).encode()))
        assert Impact(manifest, directory / "impact.json.gz", "pool-noop").select_ids(patch) == broad
        stale.unlink()
        assert Impact(manifest, directory / "impact.json.gz", "pool-noop").select_ids(patch) == broad

    second = "sqlglot/time.py"
    extra = patch_for(second, impact.sources[second],
                      impact.sources[second] + "\n# benign second file\n")
    assert impact.select_ids(patch + extra) == impact.all_ids
    print("lambda call map and structural fallback guards passed")


if __name__ == "__main__":
    main()
