#!/usr/bin/env bash
# proxy CPU, modello denso, non AMD. Ginocchio a T=8: verify-only (d=0), T in {1,6,7,8,9,10} (T=1 = normalizzazione s).
# Stessa config del P4 esteso (contesto MTP presente, ms = solo forward target). --no-repack.
# v2 (03:1x CET): ON/OFF interleaved a blocchi ABBA: on,off,off,on,on,off,off,on x 25 rep = 100 rep per braccio (x 6 prompt = 600 campioni).
# Controlli (build ON): ctrl_ub256 (-t 6 -ub 256), ctrl_t8 (-t 8 -ub 512), 100 rep ciascuno. Ordine dei T ruotato per rep e invertito sulle rep dispari.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11/knee; mkdir -p $OUT
L=/workspace/llama.cpp
LOG=/workspace/strata-plus/traces/raw/v11/campaign.log
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
while [ ! -f /workspace/strata-plus/traces/raw/v11/manifest.done ]; do sleep 15; done
log "START knee build (build-nollamafile + 2 binari)"
NAT=$(grep -oP 'GGML_NATIVE:BOOL=\K\w+' $L/build/CMakeCache.txt || echo ON)
cmake -S $L -B $L/build-nollamafile -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_LLAMAFILE=OFF -DLLAMA_CURL=OFF -DGGML_NATIVE=$NAT > logs/nollamafile_cmake.log 2>&1 && \
ninja -C $L/build-nollamafile -j 8 llama-common > logs/nollamafile_build.log 2>&1 || { log "FAILED nollamafile build"; exit 1; }
for v in on:build:v11knee off:build-nollamafile:v11knee.nollamafile; do IFS=: read n b o <<< "$v"
c++ -std=c++17 -O3 -DNDEBUG -DGGML_BACKEND_SHARED -DGGML_SHARED -DGGML_USE_CPU -DLLAMA_SHARED -I$L/common -I$L/vendor -I$L/include -I$L/ggml/include -I/workspace/strata-src/include proxy/llama_spec_trace.cpp build-strata-cpu/libstrata_spec.a -L$L/$b/bin -lllama-common -lllama -lggml -lggml-base -Wl,-rpath,$L/$b/bin -o proxy/llama_spec_trace.$o.bin >> logs/knee_build.log 2>&1 || { log "FAILED knee build $n"; exit 1; }
done
grep -E "GGML_LLAMAFILE" $L/build/CMakeCache.txt $L/build-nollamafile/CMakeCache.txt >> logs/knee_build.log
log "END knee build"
COMMON="--spec-type draft-mtp --spec-draft-n-max 8 --temp 0 -n 8 -c 4096 -b 4096 --no-repack --prompts datasets/p4_prompts.jsonl --dmax 7 --mode p4 --p4-tlist 1,6,7,8,9,10"
./proxy/llama_spec_trace.v11knee.bin -m models/qwen35-2b-mtp-q4_k_m.gguf $COMMON -t 6 -ub 512 --limit 1 --p4-reps 2 --tag knee_smoke --out $OUT/knee_smoke 2> $OUT/knee_smoke.err || { log "FAILED knee smoke"; exit 1; }
heavy() { ps -eo pcpu,args --no-headers | awk '$1>50' | grep -v -E "ps -eo|awk|llama_spec_trace" | wc -l; }
pscheck() { echo "== $(date '+%F %T %Z') $1"; ps -eo pid,pcpu,rss,etimes,args --sort=-pcpu | head -8; }
: > $OUT/cmds.txt
for m in "q4km models/qwen35-2b-mtp-q4_k_m.gguf" "q8 models/qwen35-2b-mtp-q8_0.gguf"; do set -- $m; mt=$1; mp=$2
for cfg in "main_b1 v11knee 25 -t 6 -ub 512" "llamafile_off_b2 v11knee.nollamafile 25 -t 6 -ub 512" "llamafile_off_b3 v11knee.nollamafile 25 -t 6 -ub 512" "main_b4 v11knee 25 -t 6 -ub 512" \
           "main_b5 v11knee 25 -t 6 -ub 512" "llamafile_off_b6 v11knee.nollamafile 25 -t 6 -ub 512" "llamafile_off_b7 v11knee.nollamafile 25 -t 6 -ub 512" "main_b8 v11knee 25 -t 6 -ub 512" \
           "ctrl_ub256 v11knee 100 -t 6 -ub 256" "ctrl_t8 v11knee 100 -t 8 -ub 512"; do
  set -- $cfg; name=${mt}_$1; bin=./proxy/llama_spec_trace.$2.bin; reps=$3; shift 3
  ok=0; for i in $(seq 1 240); do
    if [ "$(heavy)" -eq 0 ] && [ "$(pgrep -fc run_v2.py)" -eq 0 ]; then ok=$((ok+1)); else ok=0; echo "$(date '+%T') busy" >> $OUT/ps.log; fi
    [ $ok -ge 3 ] && break; sleep 5; done
  pscheck "BEFORE knee_$name (ok=$ok)" >> $OUT/ps.log
  ( while true; do sleep 5; pscheck "DURING knee_$name" >> $OUT/ps.log; done ) & MON=$!
  echo "$bin -m $mp $COMMON --p4-reps $reps $* --tag knee_$name --out $OUT/knee_$name" >> $OUT/cmds.txt
  log "START knee_$name ($*)"
  $bin -m $mp $COMMON --p4-reps $reps "$@" --tag knee_$name --out $OUT/knee_$name 2> $OUT/knee_$name.err
  log "END knee_$name exit $?"
  kill $MON
done; done
python3 tools/knee_t8.py >> $LOG 2>&1
touch /workspace/strata-plus/traces/raw/v11/knee.done
