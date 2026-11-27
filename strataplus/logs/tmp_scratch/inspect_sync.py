#!/usr/bin/env python3
import subprocess
from pathlib import Path

REPO = "/workspace/strataplus-backup"
SRC = "/workspace/strata-src"
PREV_HEAD = "9d823158ad30676321b09c26318f85a6aa5179d4"

def git(cmd, cwd=REPO):
    r = subprocess.run(cmd, cwd=cwd, shell=True, text=True, capture_output=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def p(title):
    print()
    print("===", title, "===")

p("LOCAL BACKUP HEADS")
for cmd in [
    "git rev-parse --abbrev-ref HEAD",
    "git rev-parse HEAD",
    "git rev-parse --short HEAD",
    "git log -1 --format='%h %ad %s' --date=iso-local",
    "git rev-parse --verify refs/heads/strataplus-policy-local",
    "git rev-parse --verify refs/heads/strataplus-pt12-measure",
]:
    out, err, rc = git(cmd)
    print(cmd, "->", out or err)

p("COMMIT STAT vs previous")
out, err, rc = git(f"git show --stat --format=fuller --date=iso-local {PREV_HEAD}..HEAD")
print(out or err)

p("NAME-STATUS")
out, err, rc = git(f"git diff --name-status {PREV_HEAD}..HEAD")
print(out or err)

p("SRC_GIT BRANCHES")
out, err, rc = git(
    "git branch -a --format='%(refname:short)|%(objectname:short)|%(committerdate:iso-local)|%(subject)'",
    cwd=SRC,
)
print(out or err)

p("BACKUP REPO LOCAL BRANCHES")
out, err, rc = git(
    "git branch --format='%(refname:short)|%(objectname:short)|%(committerdate:iso-local)|%(subject)'"
)
print(out or err)
