#!/usr/bin/env bash
# Build HIP del binario strata (gfx1100) per patch (hfc_worktree, v1) e controllo 7dd5cf1 (orig_7dd5cf1), stesso comando,
# nice 19 -j1, log separati, confronto warning.  NON eseguito dall'esecutore (rinviato dopo la finestra di misura).
# Uso: ./hfc_hip_build_deferred.sh [v1|v2]   (default v1; v2 usa hfc_v2_worktree)
set -u
cd /workspace/scout-local
LOG=/workspace/scout/cpu_busy_scout.log
TAG=${1:-v1}
case $TAG in v1) PSRC=hfc_worktree; PB=hfc_build_hip;; v2) PSRC=hfc_v2_worktree; PB=hfc_v2_build_hip;; *) echo "v1|v2"; exit 2;; esac
[ -d orig_7dd5cf1 ] || git -C hfc_worktree worktree add --detach /workspace/scout-local/orig_7dd5cf1 7dd5cf1
CFG="cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_HIP=ON -DCMAKE_HIP_COMPILER=/usr/bin/clang++-17 -DCMAKE_CXX_COMPILER=clang++-17 -DCMAKE_C_COMPILER=clang-17 -DCMAKE_HIP_ARCHITECTURES=gfx1100 -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
run() { local L=$1 O=$2; shift 2; echo "START $(date '+%F %T %Z') $L" >> $LOG; nice -n 19 "$@" > "$O" 2>&1; local rc=$?; echo "END $(date '+%F %T %Z') rc=$rc $L" >> $LOG; return $rc; }
for side in patch orig; do
  if [ $side = patch ]; then S=$PSRC; B=$PB; else S=orig_7dd5cf1; B=orig_build_hip; fi
  run "cmake HIP gfx1100 $side($TAG)" deferred_cfg_${side}_$TAG.log $CFG -S $S -B $B
  run "ninja -j1 strata HIP gfx1100 $side($TAG)" deferred_build_${side}_$TAG.log ninja -C $B -j1 -k 0 strata; echo "$side rc=$?"
done
norm(){ sed -E 's#/workspace/scout-local/[a-z0-9_]+(worktree|7dd5cf1)#SRC#g; s#/workspace/scout-local/[a-z0-9_]+build_hip#BLD#g' "$1" | grep -E 'warning:' | sed -E 's#:[0-9]+:[0-9]+:#:L:C:#' | sort; }
norm deferred_build_patch_$TAG.log > deferred_w_patch_$TAG.txt; norm deferred_build_orig_$TAG.log > deferred_w_orig_$TAG.txt
wc -l deferred_w_patch_$TAG.txt deferred_w_orig_$TAG.txt
diff deferred_w_orig_$TAG.txt deferred_w_patch_$TAG.txt > deferred_w_diff_$TAG.txt && echo "warning identici" || echo "warning diversi: deferred_w_diff_$TAG.txt"
grep '^FAILED' deferred_build_patch_$TAG.log deferred_build_orig_$TAG.log
