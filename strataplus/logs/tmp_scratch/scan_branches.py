import os, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROME = timezone(timedelta(hours=1))

def fmt(ts):
    return datetime.fromtimestamp(ts, ROME).strftime("%Y-%m-%d %H:%M %Z")

KNOWN_LOCAL_BRANCHES = {
    "strataplus-h1-hlang-local",
    "strataplus-h1-hlang-v2-local",
    "scout-hfc-local",
    "strataplus-research",
    "strataplus-policy-local",
    "strataplus-pt12-measure",
    "feat/hlw-window12",
    "feat/dsv41-engram-q5k",
    "main",
    "master",
}
COVERED_BRANCHES = {
    "strataplus-research",
    "strataplus-policy-local",
    "strataplus-pt12-measure",
}

repos = []
for root, dirs, files in os.walk("/workspace"):
    depth = root[len("/workspace"):].count(os.sep)
    if depth > 3:
        dirs[:] = []
        continue
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", ".cache", "models", "rocm"}
    dirs[:] = [d for d in dirs if d not in skip]
    if Path(root, ".git").exists():
        repos.append(root)
        dirs[:] = [d for d in dirs if d != ".git"]

print("=== git repos ===")
branch_info = []
for repo in sorted(set(repos)):
    try:
        out = subprocess.check_output(
            ["git", "-C", repo, "for-each-ref", "--format=%(refname:short)|%(committerdate:iso-strict)|%(objectname:short)|%(subject)", "refs/heads"],
            text=True, stderr=subprocess.DEVNULL, timeout=20)
    except Exception as e:
        print("%s: err %s" % (repo, e))
        continue
    print("\nREPO %s" % repo)
    for line in out.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 3)
        name, date, sha, subj = (parts + [""] * 4)[:4]
        print("  %s  %s  %s  %s" % (name, date, sha, subj[:80]))
        branch_info.append({"repo": repo, "name": name, "date": date, "sha": sha, "subject": subj})

print("\n=== uncovered or possibly new local branches ===")
cutoff = "2026-11-12"
for b in branch_info:
    name = b["name"]
    date = b["date"]
    if name in COVERED_BRANCHES:
        continue
    is_known = name in KNOWN_LOCAL_BRANCHES
    newish = date[:10] >= cutoff if date else False
    if (not is_known) or newish:
        print("  FLAG known=%s newish=%s %s %s %s %s %s" % (is_known, newish, b["repo"], name, date, b["sha"], b["subject"][:80]))

print("\n=== /workspace top-level ===")
root = Path("/workspace")
for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
    try:
        st = p.stat()
        typ = "dir" if p.is_dir() else "file"
        print("  %s  %s  mtime  %s" % (typ, fmt(st.st_mtime), p.name))
    except Exception as e:
        print("  err %s: %s" % (p, e))

print("\n=== dirs with mtime after 2026-11-12 (Europe/Rome) ===")
cutoff_ts = datetime(2026, 11, 12, 13, 48, tzinfo=ROME).timestamp()
remat_lo = datetime(2026, 11, 24, 20, 0, tzinfo=ROME).timestamp()
remat_hi = datetime(2026, 11, 25, 2, 0, tzinfo=ROME).timestamp()
candidates = []
for dirpath, dirnames, filenames in os.walk("/workspace"):
    depth = Path(dirpath).relative_to("/workspace").parts
    if len(depth) > 2:
        dirnames[:] = []
        continue
    base = depth[0] if depth else ""
    if base in {".cache", "node_modules", "models", "rocm", "browser-cdp", "screenshots"}:
        dirnames[:] = []
        continue
    try:
        mt = os.stat(dirpath).st_mtime
    except OSError:
        continue
    if mt >= cutoff_ts:
        remat = remat_lo <= mt <= remat_hi
        candidates.append((mt, remat, dirpath))

for mt, remat, rel in sorted(candidates, reverse=True)[:80]:
    flag = "REMAT?" if remat else "AFTER_STOP"
    print("  %s  %s  %s" % (flag, fmt(mt), rel))

print("\nDONE")
