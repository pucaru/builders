"""Label a control-flow relocation that an equal-line-count diff can conceal.

Usage: python tools/relocation_regression.py PINNED_SQLGLOT TESTS_JSON OUTPUT_DIR
The output directory is separate from the selector's map and Docker context.
"""
import difflib
import json
from pathlib import Path
import shutil
import sys

from regression import label


def main():
    root, manifest_path, output = map(lambda value: Path(value).resolve(), sys.argv[1:4])
    output.mkdir()
    logs = output / "logs"
    patches = output / "data" / "commits"
    logs.mkdir()
    patches.mkdir(parents=True)
    shutil.copyfile(manifest_path, patches.parent / "tests.json")

    name = "relocated-return"
    path = "sqlglot/generator.py"
    old = (root / path).read_text()
    anchor = '    def property_sql(self, expression: exp.Property) -> str:\n'
    ending = '            self.unsupported(f"Unsupported property {expression.key}")\n'
    if old.count(anchor) != 1 or old.count(ending) != 1:
        raise ValueError("unexpected pinned helper source")
    new = old.replace(anchor, anchor + '        return ""\n', 1).replace(ending, "", 1)
    diff = difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                f"a/{path}", f"b/{path}", n=24)
    (patches / f"{name}.patch").write_text(
        f"diff --git a/{path} b/{path}\n" + "".join(diff))

    manifest = json.loads(manifest_path.read_text())["tests"]
    key, result = label(root, logs, name, {path: new}, manifest, 900, 2)
    (output / "answers.json").write_text(json.dumps({"commits": {key: result}}))
    print(f"{name}: {len(result['failing'])} failing tests in {result['seconds']} s")


if __name__ == "__main__":
    main()
