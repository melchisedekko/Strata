#!/usr/bin/env python3
import os, subprocess, sys
token = os.environ.get("GITHUB_TOKEN") or ""
p = subprocess.run(["bash", "/workspace/strataplus-backup/sync.sh"], capture_output=True, text=True)
out = (p.stdout or "")
if p.stderr:
    out += ("\n" if out and not out.endswith("\n") else "") + p.stderr
if token:
    out = out.replace(token, "[REDACTED]")
sys.stdout.write(out)
if not out.endswith("\n"):
    sys.stdout.write("\n")
print("SYNC_EXIT=%d" % p.returncode)
