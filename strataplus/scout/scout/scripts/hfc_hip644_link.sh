#!/usr/bin/env bash
# Link completo di `strata` HIP con ROCm 6.4.4 (gfx1100;gfx1201): patch H-FC v2 vs controllo 7dd5cf1.
# Stesso comando cmake/ninja per entrambe, nice 19, -j2 -k 0, sequenziali.  DRY=1 stampa i comandi senza eseguire cmake/ninja/test.
# L'env ROCm 6.4.4 viene caricato SOLO in questo processo (mai globale: rompe /usr/bin/hipcc 5.7).
set -u
DRY=${DRY:-0}
SL=/workspace/scout-local
REPO=/workspace/Strata
BASE=7dd5cf1
PATCH=/workspace/scout/patches/strataplus-HFC-frozen-v2.patch
PSHA=f5a02954320b39aaa6f385a3d5536dc9e25c2306d1248ed44ac9e61a6af355b5
PWT=$SL/hfc_v2_worktree
CWT=$SL/ctl644_7dd5cf1
LOG=/workspace/scout/cpu_busy_scout.log
TPC=/workspace/strata-policy/patches/strataplus-serve-trace-v1.patch
TPCSHA=2875566df6d7bffc7537465e726d861422ae2eb3e49d02b5bb7c24259ae02489
TPH=/workspace/strata-policy/patches/strataplus-serve-trace-v1-on-HFCv2.patch
TPHSHA=1a227fad6a9817f29c5dc1f537d212afc7ae159e296dcd141bd7a42fea93011f
TCWT=$SL/trace_ctl_7dd5cf1
THWT=$SL/trace_hfc_7dd5cf1
cd $SL || exit 1

# 1. sha256 patch
got=$(sha256sum "$PATCH" | cut -d' ' -f1)
[ "$got" = "$PSHA" ] || { echo "ERRORE: sha256 patch $got != $PSHA"; exit 3; }
echo "patch sha256 OK"

# 2. worktree (operazioni git leggere, eseguite anche in DRY se mancano)
if [ ! -d $CWT ]; then git -C $REPO worktree add --detach $CWT $BASE || exit 4; fi
[ "$(git -C $CWT rev-parse --short=7 HEAD)" = $BASE ] && [ -z "$(git -C $CWT status --porcelain)" ] || { echo "ERRORE: controllo non pulito a $BASE"; exit 4; }
if [ ! -d $PWT ]; then git -C $REPO worktree add --detach $PWT $BASE && git -C $PWT apply --index "$PATCH" || exit 5; fi
dsha=$(git -C $PWT diff $BASE | sha256sum | cut -d' ' -f1)
[ "$dsha" = "$PSHA" ] || { echo "ERRORE: git diff $BASE in $PWT ($dsha) non corrisponde alla patch"; exit 5; }
echo "worktree patch = v2 OK; controllo pulito OK"

# 2b. trace_ctl / trace_hfc: sha delle patch, worktree dedicati, git apply in ordine (stop alla prima che fallisce)
for pf in "$TPC:$TPCSHA" "$TPH:$TPHSHA"; do
  f=${pf%%:*}; e=${pf##*:}; g=$(sha256sum "$f" | cut -d' ' -f1)
  [ "$g" = "$e" ] || { echo "ERRORE: sha256 $f $g != $e"; exit 3; }
done
echo "trace patch sha256 OK"
mkwt() { local W=$1; shift
  [ -d $W ] && { echo "worktree $W gia' presente: riuso"; return 0; }
  git -C $REPO worktree add --detach $W $BASE || return 1
  for p in "$@"; do
    if git -C $W apply --index "$p"; then echo "git apply OK: $(basename $p) -> $W"
    else echo "ERRORE: git apply fallito: $p su $W"; return 1; fi
  done; }
mkwt $TCWT "$TPC" || exit 6
mkwt $THWT "$PATCH" "$TPH" || exit 7
for W in $TCWT $THWT; do [ "$(git -C $W rev-parse --short=7 HEAD)" = $BASE ] || { echo "ERRORE: $W non a $BASE"; exit 6; }; done
echo "worktree trace_ctl/trace_hfc OK"

# Env ROCm 6.4.4 solo qui dentro
source /workspace/rocm-6.4.4.env
R=/opt/rocm-6.4.4
CFG=(cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_HIP=ON -DSTRATA_BUILD_TESTS=ON
     -DCMAKE_HIP_COMPILER=$R/llvm/bin/clang++ -DCMAKE_CXX_COMPILER=$R/llvm/bin/clang++ -DCMAKE_C_COMPILER=$R/llvm/bin/clang
     "-DCMAKE_HIP_ARCHITECTURES=gfx1100;gfx1201" "-DGPU_TARGETS=gfx1100;gfx1201" "-DAMDGPU_TARGETS=gfx1100;gfx1201"
     -DCMAKE_PREFIX_PATH=$R -DCMAKE_EXPORT_COMPILE_COMMANDS=ON)
echo "== toolchain 6.4.4"; $R/bin/hipcc --version 2>&1 | head -3; $R/llvm/bin/clang++ --version | head -1

run() { local L=$1 O=$2; shift 2
  echo "CMD[$L]: nice -n 19 $* > $O"
  [ "$DRY" = 1 ] && return 0
  echo "START $(date '+%F %T %Z') $L" >> $LOG; nice -n 19 "$@" > "$O" 2>&1; local rc=$?
  echo "END $(date '+%F %T %Z') rc=$rc $L" >> $LOG; echo "$L rc=$rc"; return $rc; }

# 3. build sequenziali
for side in patch ctl; do
  [ $side = patch ] && S=$PWT || S=$CWT; B=$SL/build644_$side
  run "cmake HIP644 $side" link644_cfg_$side.log "${CFG[@]}" -S $S -B $B
  run "ninja -j2 strata HIP644 $side" link644_build_$side.log ninja -C $B -j2 -k 0 strata
done
B=$SL/build644_patch
run "ninja -j2 policy tests HIP644 patch" link644_tests_patch.log ninja -C $B -j2 -k 0 draft_policy_frozen_test draft_policy_test

# 4. trace_ctl poi trace_hfc, stesso comando, una alla volta
for side in trace_ctl trace_hfc; do
  [ $side = trace_ctl ] && S=$TCWT || S=$THWT; B=$SL/build644_$side
  run "cmake HIP644 $side" link644_cfg_$side.log "${CFG[@]}" -S $S -B $B
  run "ninja -j2 strata HIP644 $side" link644_build_$side.log ninja -C $B -j2 -k 0 strata
done
B=$SL/build644_patch

[ "$DRY" = 1 ] && { echo "DRY=1: niente eseguito oltre ai controlli"; exit 0; }

# 5. FAILED, warning, sha
grep -H '^FAILED' link644_build_patch.log link644_build_ctl.log link644_tests_patch.log link644_build_trace_ctl.log link644_build_trace_hfc.log > link644_failed.txt; echo "FAILED: $(wc -l < link644_failed.txt) righe (link644_failed.txt)"
norm(){ sed -E "s#$PWT#SRC#g; s#$CWT#SRC#g; s#$TCWT#SRC#g; s#$THWT#SRC#g; s#$SL/build644_(patch|ctl|trace_ctl|trace_hfc)#BLD#g" "$1" | grep -E 'warning:' | sed -E 's#:[0-9]+:[0-9]+:#:L:C:#' | sort; }
norm link644_build_patch.log > link644_w_patch.txt; norm link644_build_ctl.log > link644_w_ctl.txt
wc -l link644_w_patch.txt link644_w_ctl.txt
diff link644_w_ctl.txt link644_w_patch.txt > link644_w_diff.txt && echo "warning identici" || echo "warning diversi: link644_w_diff.txt"
norm link644_build_trace_ctl.log > link644_w_trace_ctl.txt; norm link644_build_trace_hfc.log > link644_w_trace_hfc.txt
wc -l link644_w_trace_ctl.txt link644_w_trace_hfc.txt
diff link644_w_trace_ctl.txt link644_w_trace_hfc.txt > link644_w_diff_trace.txt && echo "warning trace identici" || echo "warning trace diversi: link644_w_diff_trace.txt"
for side in patch ctl trace_ctl trace_hfc; do f=$SL/build644_$side/strata; [ -f $f ] && sha256sum $f || echo "manca $f"; done

# 6. test host
for t in draft_policy_frozen_test draft_policy_test; do
  if [ -x $B/$t ]; then run "test $t" link644_$t.log $B/$t; tail -3 link644_$t.log
  elif grep -q "^build $t" $B/build.ninja 2>/dev/null || grep -q " $t:" $B/build.ninja 2>/dev/null; then echo "target $t presente ma binario non creato"
  else echo "target $t NON esiste in questa configurazione"; fi
done
