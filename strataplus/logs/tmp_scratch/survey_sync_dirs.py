#!/usr/bin/env python3
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import subprocess

rome = timezone(timedelta(hours=1))
cutoff = datetime(2026, 11, 18, 20, 19, tzinfo=rome).timestamp()

watch = [
    "/workspace/strata-plus",
    "/workspace/strata-policy",
    "/workspace/strata-bench",
    "/workspace/scout",
    "/workspace/scout-local",
    "/workspace/policy-local",
    "/workspace/strata-src",
    "/workspace/Strata",
    "/workspace/strata",
    "/workspace/replay",
]

def mtime(p):
    try:
        return os.lstat(p).st_mtime
    except OSError:
        return 0

print("=== top-level watch dirs ===")
for d in watch:
    p = Path(d)
    if not p.exists():
        print("MISSING", d)
        continue
    ts = datetime.fromtimestamp(os.lstat(d).st_mtime, rome).strftime("%Y-%m-%d %H:%M:%S %Z")
    kind = "dir" if p.is_dir() else "other"
    print(f"{ts}  {kind}  {d}")

print()
print("=== dirs under team roots touched since 2026-11-18 20:19 Rome (depth<=3) ===")
seen = 0
prune = {".git", "__pycache__", ".venv", "venv", "node_modules", "models", "build", "build-strata-cpu"}
for root in watch:
    rp = Path(root)
    if not rp.is_dir():
        continue
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [n for n in dirnames if n not in prune]
        depth = Path(dirpath).relative_to(root).parts
        if len(depth) > 3:
            dirnames[:] = []
            continue
        mt = mtime(dirpath)
        if mt < cutoff:
            continue
        ts = datetime.fromtimestamp(mt, rome).strftime("%Y-%m-%d %H:%M:%S")
        newfiles = []
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            if mtime(fp) >= cutoff:
                newfiles.append(fn)
        print(f"{ts}  {dirpath}  touched_files={len(newfiles)}")
        for fn in newfiles[:15]:
            print("   ", fn)
        seen += 1
        if seen > 80:
            print("...truncated...")
            break
    if seen > 80:
        break

print()
print("=== git branches in team repos ===")
for repo in [
    "/workspace/strata-src",
    "/workspace/strata-policy",
    "/workspace/strata-bench",
    "/workspace/llama.cpp",
    "/workspace/Strata",
    "/workspace/strata",
    "/workspace/scout",
    "/workspace/policy-local",
    "/workspace/scout-local",
]:
    if not (Path(repo) / ".git").exists():
        if Path(repo).exists():
            print(f"{repo}: no .git")
        continue
    out = subprocess.check_output(
        ["git", "-C", repo, "branch", "--format=%(refname:short) %(objectname:short)"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    print(f"--- {repo} ---")
    print(out.rstrip() or "(none)")
