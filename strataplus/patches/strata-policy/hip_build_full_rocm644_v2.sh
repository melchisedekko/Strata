#!/usr/bin/env bash
# Strata+ v2 + serve-trace v1 (copy of hip_build_full_rocm644.sh, which is unchanged): FULL link with ROCm 6.4.4,
# gfx1100;gfx1201, six SEQUENTIAL builds (one at a time):
#   (1) ctrl : control b24c6a1d
#   (2) h1   : b24c6a1d + strataplus-H1-arbiter-v2.patch
#   (3) full : b24c6a1d + strataplus-H1-arbiter-v2.patch + strataplus-LANG-knob-v2.patch
#   (4) fullst : (3) + strataplus-serve-trace-v1-on-H1v2-LANGv2.patch
#   (5) ctrlst : b24c6a1d + strataplus-serve-trace-v1.patch
#   (6) h1st : (2) + strataplus-serve-trace-v1-on-H1v2.patch (Lead 26/10 22:45: H1 alone measured in serve)
# Same configure+build command for all six; nice 19, ninja -j2; times in /workspace/strata-plus/cpu_busy_policy.log.
# Per build: rc, exact command, warning multiset vs control, sha256 of the strata binary.  If (1) does not link, (2)-(6)
# build only the touched objects (generate.cpp.o + strata_spec) and the summary says so.
# DO NOT RUN during Bench's a' window: usage  hip_build_full_rocm644.sh --bench-window-ended
# The ROCm env is sourced only inside this script's shell (never globally: it breaks /usr/bin/hipcc 5.7).
set -u
[ "${1:-}" = --bench-window-ended ] || { echo "usage: $0 --bench-window-ended   (only after Bench announces the end of a')"; exit 2; }
if pgrep -af aprime | grep -v pgrep >/dev/null; then echo "an aprime process is running: refusing"; exit 2; fi
P=/workspace/policy-local; L=/workspace/strata-plus/cpu_busy_policy.log; O=$P/logs/rocm644_v2; mkdir -p "$O"
PD=/workspace/strata-policy/patches; H1=$PD/strataplus-H1-arbiter-v2.patch; LG=$PD/strataplus-LANG-knob-v2.patch
ST=$PD/strataplus-serve-trace-v1.patch; STV=$PD/strataplus-serve-trace-v1-on-H1v2-LANGv2.patch
STH=$PD/strataplus-serve-trace-v1-on-H1v2.patch
REPO=$P/main_ctrl; BASE=b24c6a1d
source /workspace/rocm-6.4.4.env
HIPCXX=/opt/rocm-6.4.4/llvm/bin/clang++
SUM=$O/summary.txt; : > "$SUM"
say() { echo "$*" | tee -a "$SUM"; }
say "== $(date '+%F %T %Z') hip_build_full_rocm644_v2.sh"
say "ROCm: $(cat /opt/rocm-6.4.4/.info/version 2>/dev/null || echo '?')  hipconfig: $(/opt/rocm-6.4.4/bin/hipconfig --version 2>/dev/null || echo '?')"
say "clang: $($HIPCXX --version | head -1)"
say "patch sha256: $(sha256sum "$H1")"
say "patch sha256: $(sha256sum "$LG")"
say "patch sha256: $(sha256sum "$ST")"
say "patch sha256: $(sha256sum "$STV")"
say "patch sha256: $(sha256sum "$STH")"
for f in "$H1" "$LG" "$ST" "$STV" "$STH"; do
  (cd "$PD" && sha256sum -c "$(basename "$f").sha256" >/dev/null) || { say "sha256 mismatch for $f: abort"; exit 2; }
done
norm() { grep "warning:" "$1" | sed -E 's#^[^ ]*:[0-9]+:[0-9]+: ##' | sed -E "s#$P/rocm644v2_[a-z0-9_]+#ROOT#g" | sort; }

# sources: fresh detached worktrees of b24c6a1d with the patches applied (git apply, as a user would)
mksrc() {  # name patches...
  local s=$P/rocm644v2_src_$1; shift
  if [ -e "$s" ]; then git -C "$REPO" worktree remove --force "$s" 2>/dev/null || rm -rf "$s"; fi
  git -C "$REPO" worktree prune
  git -C "$REPO" worktree add -q --detach "$s" "$BASE" || return 1
  for p in "$@"; do git -C "$s" apply "$p" || { echo "git apply $p failed"; return 1; }; done
}
mksrc ctrl || exit 1
mksrc h1 "$H1" || exit 1
mksrc full "$H1" "$LG" || exit 1
mksrc fullst "$H1" "$LG" "$STV" || exit 1
mksrc ctrlst "$ST" || exit 1
mksrc h1st "$H1" "$STH" || exit 1

CFG=(-G Ninja -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_HIP=ON -DSTRATA_PREFILL_MMQ=ON
     "-DCMAKE_HIP_ARCHITECTURES=gfx1100;gfx1201" -DCMAKE_HIP_COMPILER=$HIPCXX
     -DSTRATA_GGML_DIR=/workspace/strata-bench/build-strata-cpu/_deps/strata_llamacpp-src)
TOUCHED="CMakeFiles/strata.dir/src/program/generate.cpp.o strata_spec"   # strata_spec includes serve_trace.cpp in (4)/(5)/(6)
ctrl_linked=0
for tag in ctrl h1 full fullst ctrlst h1st; do
  s=$P/rocm644v2_src_$tag; b=$P/rocm644v2_build_$tag; rm -rf "$b"
  if [ $tag = ctrl ] || [ $ctrl_linked = 1 ]; then tgt=strata; mode="FULL LINK"; else tgt=$TOUCHED; mode="TOUCHED OBJECTS ONLY (control did not link)"; fi
  cmd_cfg="nice -n 19 cmake -S $s -B $b ${CFG[*]}"
  cmd_bld="nice -n 19 ninja -C $b -j2 -v $tgt"
  t0=$(date '+%F %T')
  echo "$t0 | (in corso) | INIZIO rocm644 $tag gfx1100;gfx1201 $mode, nice 19 -j2 | rc=pending" >> "$L"
  nice -n 19 cmake -S "$s" -B "$b" "${CFG[@]}" > "$O/$tag.configure.log" 2>&1; rc_cfg=$?
  rc=$rc_cfg
  if [ $rc_cfg = 0 ]; then nice -n 19 ninja -C "$b" -j2 -v $tgt > "$O/$tag.build.log" 2>&1; rc=$?; else : > "$O/$tag.build.log"; fi
  echo "$t0 | $(date '+%F %T') | FINE rocm644 $tag $mode | rc=$rc (configure rc=$rc_cfg)" >> "$L"
  bin=$(find "$b" -maxdepth 2 -type f -name strata -perm -u+x 2>/dev/null | head -1)
  sha=$([ -n "$bin" ] && sha256sum "$bin" | cut -d' ' -f1 || echo none)
  [ $tag = ctrl ] && [ $rc = 0 ] && [ -n "$bin" ] && ctrl_linked=1
  say "-- $tag [$mode] $t0 -> $(date '+%T')  configure rc=$rc_cfg  build rc=$rc  warnings=$(grep -c warning: "$O/$tag.build.log")"
  say "   configure: $cmd_cfg"
  say "   build:     $cmd_bld"
  say "   strata binary: ${bin:-none}  sha256=$sha"
done
for tag in h1 full fullst ctrlst h1st; do
  if [ $ctrl_linked = 1 ]; then ref=$O/ctrl.build.log; else
    # control without link: compare against the control's warnings on the same touched objects only
    # control without link: the control's touched objects alone, fresh build dir, same command
    ref=$O/ctrl_touched.build.log
    if [ ! -e "$ref" ]; then
      b=$P/rocm644v2_build_ctrl_touched; rm -rf "$b"; t0=$(date '+%F %T')
      echo "$t0 | (in corso) | INIZIO rocm644 ctrl_touched (oggetti toccati) | rc=pending" >> "$L"
      nice -n 19 cmake -S "$P/rocm644v2_src_ctrl" -B "$b" "${CFG[@]}" > "$O/ctrl_touched.configure.log" 2>&1 &&
        nice -n 19 ninja -C "$b" -j2 -v $TOUCHED > "$ref" 2>&1; rc=$?
      echo "$t0 | $(date '+%F %T') | FINE rocm644 ctrl_touched | rc=$rc" >> "$L"
      say "-- ctrl_touched [TOUCHED OBJECTS ONLY] rc=$rc  build: nice -n 19 ninja -C $b -j2 -v $TOUCHED"
    fi
  fi
  if diff <(norm "$O/$tag.build.log") <(norm "$ref") > "$O/$tag.warn.diff"; then say "warning multiset $tag vs ctrl: SAME"
  else say "warning multiset $tag vs ctrl: DIFFER ($O/$tag.warn.diff, $(grep -c '^[<>]' "$O/$tag.warn.diff") lines)"; fi
done
[ $ctrl_linked = 1 ] || say "NOTE: the control b24c6a1d did NOT link with ROCm 6.4.4: (2)-(6) compiled only $TOUCHED"
say "summary: $SUM"
