"""Fail before submission if a Docker COPY input is absent from the build context.

This repository intentionally starts .dockerignore with ** and explicitly
allows the small runtime payload. Reject other ignore styles until reviewed.
"""
from pathlib import Path
import shlex


root = Path(__file__).resolve().parent.parent
ignore = [line.strip() for line in (root / ".dockerignore").read_text().splitlines()
          if line.strip() and not line.lstrip().startswith("#")]
if not ignore or ignore[0] != "**" or any(
    not line.startswith("!") for line in ignore[1:]
):
    raise SystemExit("Unrecognized .dockerignore policy; inspect build context manually")
allowed = {line[1:] for line in ignore[1:]}
sources = set()
for line in (root / "Dockerfile").read_text().splitlines():
    if not line.lstrip().startswith("COPY "):
        continue
    tokens = shlex.split(line)
    if any(token.startswith("--") for token in tokens):
        raise SystemExit("COPY flags require manual build-context inspection")
    sources.update(tokens[1:-1])
missing = sorted(path for path in sources if path not in allowed or not (root / path).is_file())
if missing:
    raise SystemExit("Missing or ignored COPY inputs: " + ", ".join(missing))
print(f"Docker build context includes all {len(sources)} COPY inputs")
