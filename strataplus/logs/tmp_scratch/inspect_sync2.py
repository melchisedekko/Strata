#!/usr/bin/env python3
import os, subprocess, hashlib
from pathlib import Path
from datetime import datetime

PREV = datetime.fromisoformat("2026-11-27T02:25:49")
REPO = "/workspace/strataplus-backup"
PREV_HEAD = "9d823158ad30676321b09c26318f85a6aa5179d4"

def git(cmd, cwd=REPO):
    r = subprocess.run(cmd, cwd=cwd, shell=True, text=True, capture_output=True)
    return r.stdout, r.stderr, r.returncode

# Diff of the mysterious file only (content). Redact token if present.
token = os.environ.get("GITHUB_TOKEN", "")
out, err, rc = git(f"git diff {PREV_HEAD}..HEAD -- strataplus/logs/tmp_scratch/strataplus-sync-out.txt")
text = out
if token:
    text = text.replace(token, "[REDACTED]")
print("=== DIFF strataplus-sync-out.txt ===")
print(text)

# When was this file first added?
out, err, rc = git("git log --follow --format='%h %ad %s' --date=iso-local -- strataplus/logs/tmp_scratch/strataplus-sync-out.txt")
print("=== HISTORY of that file ===")
print(out)

# Current file content if it still exists in worktree
p = Path("/workspace/strataplus-backup/strataplus/logs/tmp_scratch/strataplus-sync-out.txt")
print("=== WORKTREE FILE EXISTS ===", p.exists(), "size", p.stat().st_size if p.exists() else 0)
if p.exists():
    body = p.read_text(errors="replace")
    if token:
        body = body.replace(token, "[REDACTED]")
    print(body)

# Known script-covered source roots
covered_exact = {
    "/workspace/strata-plus",
    "/workspace/strata-policy",
    "/workspace/scout",
    "/workspace/strata-bench",
    "/workspace/llama.cpp",
    "/workspace/strata-src",
    "/workspace/strataplus-backup",
    "/workspace/lic_rm",
}

# Find top-level /workspace entries newer than last run, and also new dirs
print("=== /workspace TOP-LEVEL (mtime, type, name) ===")
ws = Path("/workspace")
entries = []
for child in sorted(ws.iterdir(), key=lambda x: x.name):
    try:
        st = child.stat()
    except Exception as e:
        print("stat fail", child, e)
        continue
    mtime = datetime.fromtimestamp(st.st_mtime)
    kind = "dir" if child.is_dir() else "file"
    flag = "NEWER" if mtime > PREV else "old"
    print(f"{flag}\t{mtime.isoformat(timespec='seconds')}\t{kind}\t{child.name}\tsize={st.st_size}")
    entries.append((mtime, kind, child))

# Look for artifact-like dirs under /workspace not covered, and any new dirs/files since last run
# Also scan common team locations for new subfolders
print()
print("=== NEW/CHANGED ITEMS UNDER KEY ROOTS since last run (depth<=3, skip venv/git/cache) ===")
SKIP_DIR_NAMES = {".git", ".venv", "venv", "__pycache__", "node_modules", ".cache", "build", "dist", "out", "target", "coverage"}
KEY_ROOTS = [
    Path("/workspace"),
    Path("/workspace/strata-plus"),
    Path("/workspace/strata-policy"),
    Path("/workspace/scout"),
    Path("/workspace/strata-bench"),
    Path("/workspace/llama.cpp"),
    Path("/workspace/strata-src"),
]
# For /workspace itself, only immediate children already printed; also walk other research-looking folders
# Find dirs named traces, patches, artifacts, results, logs, runs, e1, policy, etc. that are new

# Walk /workspace one level deeper for dirs not in covered roots
print()
print("=== UNCOVERED /workspace dirs (not script source roots) ===")
for child in sorted(ws.iterdir(), key=lambda x: x.name):
    if not child.is_dir():
        continue
    name = child.name
    path = str(child)
    if path in covered_exact:
        continue
    # skip hidden/tool caches
    if name.startswith(".") and name not in (".important",):
        # still mention if newer and looks like research
        try:
            mtime = datetime.fromtimestamp(child.stat().st_mtime)
        except Exception:
            continue
        if mtime > PREV:
            print(f"HIDDEN_NEWER\t{mtime.isoformat(timespec='seconds')}\t{path}")
        continue
    try:
        mtime = datetime.fromtimestamp(child.stat().st_mtime)
    except Exception:
        continue
    # count files
    nfiles = 0
    newest = mtime
    try:
        for root, dirs, files in os.walk(child):
            dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES and not d.startswith(".")]
            nfiles += len(files)
            for f in files:
                try:
                    mt = datetime.fromtimestamp((Path(root)/f).stat().st_mtime)
                    if mt > newest:
                        newest = mt
                except Exception:
                    pass
            if nfiles > 5000:
                break
    except Exception as e:
        print("walk fail", path, e)
        continue
    flag = "NEWER" if newest > PREV or mtime > PREV else "old"
    print(f"{flag}\tcreated_or_dirmtime={mtime.isoformat(timespec='seconds')}\tnewest={newest.isoformat(timespec='seconds')}\tfiles~{nfiles}\t{path}")

# New files under covered roots that might be new artifact FOLDERS (directory mtime/new dirs)
print()
print("=== NEW DIRECTORIES under covered roots since last run ===")
for rootp in [Path("/workspace/strata-plus"), Path("/workspace/strata-policy"), Path("/workspace/scout"), Path("/workspace/strata-bench"), Path("/workspace/llama.cpp")]:
    if not rootp.is_dir():
        continue
    for root, dirs, files in os.walk(rootp):
        rel = Path(root).relative_to(rootp)
        # prune
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
        for d in list(dirs):
            dp = Path(root)/d
            try:
                st = dp.stat()
                # use newest ctime/mtime; also check if dir is new via birth if available
                mt = datetime.fromtimestamp(st.st_mtime)
                ct = datetime.fromtimestamp(getattr(st, "st_ctime", st.st_mtime))
            except Exception:
                continue
            # A new folder: ctime after prev run is a decent heuristic on Linux (metadata change, or birth)
            if ct > PREV or mt > PREV:
                # only report if the directory itself looks newly created: ctime after prev
                # (mtime changes when contents change, which is expected for covered folders)
                if ct > PREV:
                    print(f"NEWDIR_CTIME\t{ct.isoformat(timespec='seconds')}\tmtime={mt.isoformat(timespec='seconds')}\t{dp}")
