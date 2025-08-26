#!/usr/bin/env python3
import glob
import os
import re
import sys

MAX_LEN = 32
BAD = []

for path in glob.glob(os.path.join("backend", "alembic", "versions", "*.py")):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"revision\s*=\s*['\"]([^'\"]+)['\"]", content)
    if match:
        revision = match.group(1)
        if len(revision) > MAX_LEN:
            BAD.append((path, revision, len(revision)))
    else:
        BAD.append((path, None, 0))

if BAD:
    for path, rev, length in BAD:
        if rev is None:
            print(f"{path}: could not find revision string", file=sys.stderr)
        else:
            print(
                f"{path}: revision '{rev}' is {length} chars (max {MAX_LEN})",
                file=sys.stderr,
            )
    sys.exit(1)
print("All Alembic revision strings are <= 32 characters.")
