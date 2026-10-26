#!/usr/bin/env bash
# Strata+ research backup -> fork PUBBLICO melchisedekko/Strata, SOLO branch `strataplus-research`.
# Idempotente: ricopia le sorgenti inventariate, rigenera manifest/patch/bundle, scansiona segreti,
# committa solo se ci sono cambiamenti e fa push del solo branch strataplus-research.
# Il token viene letto SOLO da $GITHUB_TOKEN a runtime (mai scritto su file, config o URL).
# Uso:   bash /workspace/strataplus-backup/sync.sh          (NOPUSH=1 per non fare push)
set -euo pipefail
set +x
umask 022
export LC_ALL=C

REPO=/workspace/strataplus-backup
BR=strataplus-research
BASE=7dd5cf18e68c639a8773e096c5c79f971ea2a9f5          # upstream Niko1221/Strata main usato dal team
REMOTE_URL=https://github.com/melchisedekko/Strata.git
D=$REPO/strataplus
MAXSIZE=50M
SRC_GIT=/workspace/strata-src
BRANCHES=(strataplus-policy-local strataplus-pt12-measure)
NOPUSH=${NOPUSH:-0}
RUNLOG=$REPO/.sync_runs.log          # escluso dal repo (.git/info/exclude)
GITLEAKS=$(command -v gitleaks || echo /home/box/.local/bin/gitleaks)
ALLOW=$D/SECRET_SCAN_ALLOWLIST.txt   # "sha256  path" di falsi positivi verificati a mano
SELF=sync.sh                         # questo script (contiene le regex di scansione): non scansionato
T0=$(date '+%Y-%m-%d %H:%M:%S')

cd "$REPO"
[ "$(git rev-parse --abbrev-ref HEAD)" = "$BR" ] || { echo "ERRORE: $REPO non e' sul branch $BR" >&2; exit 1; }
command -v rsync >/dev/null || { echo "ERRORE: rsync mancante" >&2; exit 1; }

EXC=(--exclude='.venv/' --exclude='venv/' --exclude='__pycache__/' --exclude='*.pyc' --exclude='.cache/'
     --exclude='*.gguf' --exclude='*.safetensors' --exclude='*.bin' --exclude='*.pt' --exclude='*.pth'
     --exclude='*.o' --exclude='*.so' --exclude='*.a' --exclude='build/' --exclude='build-*/' --exclude='.git/'
     --exclude='node_modules/' --exclude='*.whl')

TMPD=$(mktemp -d); trap 'rm -rf "$TMPD"' EXIT
: > "$TMPD/large.txt"

# m <delete:0|1> <dest-subdir> <src...> [-- rsync-extra-args...]
m() {
  local del=$1 dest=$2; shift 2
  local srcs=() extra=()
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do [ -e "$1" ] && srcs+=("$1"); shift; done
  [ "${1:-}" = "--" ] && { shift; extra=("$@"); }
  [ ${#srcs[@]} -eq 0 ] && return 0
  mkdir -p "$D/$dest"
  local dflags=(); [ "$del" = 1 ] && dflags=(--delete --delete-excluded)
  rsync -a "${dflags[@]}" --max-size=$MAXSIZE "${EXC[@]}" "${extra[@]}" "${srcs[@]}" "$D/$dest/"
  # file oltre il limite: solo elenco (path, size, sha256)
  rsync -a -n --min-size=$MAXSIZE --out-format='%n' "${EXC[@]}" "${extra[@]}" "${srcs[@]}" "$D/$dest/" 2>/dev/null \
    | grep -v '/$' | while read -r rel; do
        for s in "${srcs[@]}"; do
          local cand
          if [ -d "$s" ]; then cand="${s%/}/$rel"; [ "${s: -1}" = "/" ] || cand="$(dirname "$s")/$rel"; else cand="$(dirname "$s")/$rel"; fi
          if [ -f "$cand" ]; then printf '%s\t%s\t%s\n' "$cand" "$(stat -c %s "$cand")" "$(sha256sum "$cand" | cut -d' ' -f1)" >> "$TMPD/large.txt"; break; fi
        done
      done || true
  return 0
}

# ---- plan ----
m 0 plan /workspace/strata-plus/piano.md /workspace/strata-plus/log_format.md
# (plan/PLAN_PAGE.md = export manuale della Page, non toccato dallo script)

# ---- policy ----
m 1 policy/strata-policy /workspace/strata-policy/ -- --exclude='/patchwork/' --exclude='/pt12_worktree/' --exclude='/patches/'

# ---- scout ----
m 0 scout/strata-plus /workspace/strata-plus/scout.md /workspace/strata-plus/scout_greedy_rho.md /workspace/strata-plus/scout_patch_support.md
m 1 scout/scout /workspace/scout/ -- --exclude='/Strata/' --exclude='/llama.cpp/' --exclude='/colibri/' --exclude='/HIP-CPU/' \
     --exclude='/arctic/' --exclude='/sglang/' --exclude='/vllm/'
m 0 scout/refs /workspace/issues1.txt /workspace/prs.txt /workspace/q2b_index.json /workspace/ggufhdr.py

# ---- bench ----
m 1 bench/strata-bench /workspace/strata-bench/ -- --exclude='/models/' --exclude='/logs/' --exclude='/patches/' \
     --exclude='/build-strata-cpu/' --exclude='/proxy/llama_spec_trace' --exclude='/proxy/llama_spec_trace.new' \
     --exclude='/datasets/specbench.jsonl'
m 1 bench/traces /workspace/strata-plus/traces/
m 1 bench/e1 /workspace/strata-plus/e1/ -- --exclude='/policy/data/'

# ---- logs ----
m 1 logs/strata-bench /workspace/strata-bench/logs/
m 0 logs/cpu_busy /workspace/strata-plus/cpu_busy_*.log /workspace/cpu_busy_*.log
# scratch volatile in /tmp (whitelist; senza --delete per non perdere nulla se /tmp viene svuotato)
m 0 logs/tmp_scratch /tmp/ -- --exclude='/sand-*' --exclude='/gl*.json' --exclude='/g1.json' --exclude='/jg/apply/' --exclude='/jg/apply6/' \
     --include='/annt/***' --include='/av12/***' --include='/cv12t/***' --include='/gen/***' --include='/s10/***' \
     --include='/smk/***' --include='/v11p/***' --include='/jg/***' \
     --include='/*.py' --include='/*.md' --include='/*.json' --include='/*.jsonl' --include='/*.txt' --include='/*.diff' \
     --include='/*.cu' --include='/*.cpp' --include='/*.jinja' --include='/*.bak*' --include='/*.err' --include='/*.out' \
     --include='/tf_p4.log' --exclude='*'

# ---- patches ----
m 1 patches/strata-policy /workspace/strata-policy/patches/
m 1 patches/bench /workspace/strata-bench/patches/
for b in "${BRANCHES[@]}"; do
  out=$D/patches/branches/$b
  head=$(git -C "$SRC_GIT" rev-parse -q --verify "refs/heads/$b" || true)
  [ -z "$head" ] && { echo "AVVISO: branch $b non trovato in $SRC_GIT, conservo la copia esistente"; continue; }
  if [ "$(cat "$out/HEAD" 2>/dev/null)" != "$head" ]; then
    rm -rf "$out"; mkdir -p "$out/format-patch"
    git -C "$SRC_GIT" format-patch -q --zero-commit -o "$out/format-patch" "$BASE..$head"
    git -C "$SRC_GIT" bundle create -q "$out/$b.bundle" "$BASE..refs/heads/$b"
    if [ "$(stat -c %s "$out/$b.bundle")" -gt 52428800 ]; then
      printf '%s\t%s\t%s\n' "(bundle) $b.bundle" "$(stat -c %s "$out/$b.bundle")" "$(sha256sum "$out/$b.bundle" | cut -d' ' -f1)" >> "$TMPD/large.txt"
      rm -f "$out/$b.bundle"
    fi
    git -C "$SRC_GIT" log --format='%H %ad %an%n    %s' --date=iso "$BASE..$head" > "$out/LOG.txt"
    echo "$head" > "$out/HEAD"
  fi
done
mkdir -p "$D/patches/llama.cpp"
if [ -d /workspace/llama.cpp/.git ]; then
  { echo "# llama.cpp working tree diff (non committato) su $(git -C /workspace/llama.cpp rev-parse HEAD)"; \
    git -C /workspace/llama.cpp diff; } > "$TMPD/llama.diff"
  cmp -s "$TMPD/llama.diff" "$D/patches/llama.cpp/worktree_uncommitted.diff" || cp "$TMPD/llama.diff" "$D/patches/llama.cpp/worktree_uncommitted.diff"
fi

# ---- rimozione binari ELF (output di build) ----
python3 - "$D" "$TMPD/elf.txt" <<'PY'
import os,sys
root,outp=sys.argv[1],sys.argv[2]; out=[]
for dp,dn,fn in os.walk(root):
    for f in fn:
        p=os.path.join(dp,f)
        if os.path.islink(p): continue
        try:
            with open(p,'rb') as h:
                if h.read(4)==b'\x7fELF': out.append(os.path.relpath(p,root)); os.remove(p)
        except OSError: pass
open(outp,'w').write(''.join(sorted(x+'\n' for x in out)))
PY

# ---- scansione segreti (repo PUBBLICO): file sospetti rimossi dallo staging ----
: > "$TMPD/hits.txt"
RX='(ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|ghs_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|hf_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[abprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{32,}|aws_secret_access_key|AIza[0-9A-Za-z_-]{35})'
grep -rlE -I "$RX" "$D" 2>/dev/null | sed "s|^$D/||" >> "$TMPD/hits.txt" || true
# il token reale non deve mai comparire (anche se allowlisted)
: > "$TMPD/tok.txt"
if [ -n "${GITHUB_TOKEN:-}" ]; then grep -rlF -- "$GITHUB_TOKEN" "$D" 2>/dev/null | sed "s|^$D/||" > "$TMPD/tok.txt" || true; fi
if [ -x "$GITLEAKS" ]; then
  "$GITLEAKS" dir "$D" --redact --no-banner -l error -f json -r "$TMPD/gl.json" >/dev/null 2>&1 || true
  [ -s "$TMPD/gl.json" ] && python3 -c 'import json,sys;[print(x["File"]) for x in json.load(open(sys.argv[1]))]' "$TMPD/gl.json" \
     | sed "s|^$D/||" >> "$TMPD/hits.txt" || true
  [ -s "$TMPD/gl.json" ] && cp "$TMPD/gl.json" "$REPO/.last_gitleaks.json"   # redatto, fuori dal repo
else
  echo "AVVISO: gitleaks non disponibile, solo scansione regex"
fi
sort -u "$TMPD/hits.txt" | grep -vxF "$SELF" > "$TMPD/hits2.txt" || true
: > "$TMPD/secret.txt"
while read -r f; do
  [ -z "$f" ] && continue
  [ -f "$D/$f" ] || continue
  if [ -f "$ALLOW" ] && grep -qxF "$(sha256sum "$D/$f" | cut -d' ' -f1)  $f" "$ALLOW"; then continue; fi
  echo "$f" >> "$TMPD/secret.txt"
done < "$TMPD/hits2.txt"
cat "$TMPD/tok.txt" >> "$TMPD/secret.txt"
sort -u -o "$TMPD/secret.txt" "$TMPD/secret.txt"
while read -r f; do [ -n "$f" ] && [ "$f" != "$SELF" ] && rm -f "$D/$f"; done < "$TMPD/secret.txt"
if grep -qxF "$SELF" "$TMPD/tok.txt"; then echo "ERRORE: il token compare in sync.sh!" >&2; exit 3; fi

# ---- SKIPPED.md + MANIFEST ----
{
  echo "# File esclusi dal backup (generato da sync.sh)"
  echo
  echo "## File > $MAXSIZE (non committati): path, byte, sha256"
  sort -u "$TMPD/large.txt" | sed 's/^/    /'
  echo
  echo "## Binari ELF rimossi (output di build, ricostruibili)"
  sed 's/^/    /' "$TMPD/elf.txt"
  echo
  echo "## Esclusi dalla scansione segreti (contenuto sospetto, NON pubblicato)"
  sed 's/^/    /' "$TMPD/secret.txt"
} > "$D/SKIPPED.md"
( cd "$D" && find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256 )

# ---- commit (solo se cambia qualcosa) ----
git add -A -f -- strataplus   # -f: il .gitignore upstream ignora *.log e logs/
if git diff --cached --quiet; then
  echo "Nessun cambiamento da committare."
else
  git -c user.name="Strata+ backup (melchisedekko)" -c user.email="10241980+melchisedekko@users.noreply.github.com" \
      commit -q -m "strataplus backup: sync $(TZ=Europe/Rome date '+%Y-%m-%d %H:%M %Z')"
  echo "Commit: $(git rev-parse --short HEAD)"
fi

# ---- push del SOLO branch strataplus-research sul fork (mai force) ----
if [ "$NOPUSH" != 1 ]; then
  [ -n "${GITHUB_TOKEN:-}" ] || { echo "ERRORE: GITHUB_TOKEN non impostato" >&2; exit 1; }
  AUTH=$(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 -w0)
  GIT_TERMINAL_PROMPT=0 GIT_CONFIG_COUNT=2 \
    GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0= \
    GIT_CONFIG_KEY_1=http.https://github.com/.extraHeader GIT_CONFIG_VALUE_1="Authorization: Basic $AUTH" \
    git push -q "$REMOTE_URL" "refs/heads/$BR:refs/heads/$BR" > "$TMPD/push.log" 2>&1 && prc=0 || prc=$?
  unset AUTH
  grep -v -i authorization "$TMPD/push.log" || true
  [ "$prc" = 0 ] || { echo "ERRORE: push fallito (rc=$prc)" >&2; exit "$prc"; }
  echo "Push OK: $BR -> $REMOTE_URL"
fi
echo "$T0 | $(date '+%Y-%m-%d %H:%M:%S') | sync.sh HEAD=$(git rev-parse --short HEAD)" >> "$RUNLOG"
echo "OK: HEAD $(git rev-parse HEAD)"
