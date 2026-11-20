#!/usr/bin/env python3
import os, re, subprocess
from pathlib import Path

script = Path("/workspace/strataplus-backup/sync.sh").read_text(encoding="utf-8", errors="replace")
ws_paths = sorted(set(re.findall(r"(/workspace/[^\s'"\\]+)", script)))
tmp_includes = sorted(set(re.findall(r"--include='/([^']+)'", script)))
branches = re.search(r"BRANCHES=\(([^)]+)\)", script)
branch_list = branches.group(1).split() if branches else []
print("=== SCRIPT COVERED BRANCHES ===")
print(" ".join(branch_list))
print("=== SCRIPT /workspace PATHS ===")
for p in ws_paths:
    print(p)
print("=== SCRIPT tmp includes ===")
for p in tmp_includes:
    print(p)

src = Path("/workspace/strata-src")
print("=== SRC_GIT LOCAL BRANCHES ===")
if src.exists():
    out = subprocess.check_output(["git", "-C", str(src), "for-each-ref", "--format=%(refname:short)", "refs/heads"], text=True)
    for b in out.strip().splitlines():
        print(b)
else:
    print("MISSING", src)

print("=== /workspace TOP-LEVEL ===")
for name in sorted(os.listdir("/workspace")):
    p = Path("/workspace") / name
    kind = "dir" if p.is_dir() else "file"
    print(f"{kind}\t{name}")
