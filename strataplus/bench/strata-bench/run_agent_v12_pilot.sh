#!/usr/bin/env bash
# proxy CPU, non AMD. agent_v12 PILOTA (non la serie): build proxy v12 (raw mode), alloc check -c 131072 su 1 turno corto (base),
# poi 1 turno TF Dmax=7 da 49,754 token (-c 65536) per misurare prefill/decode TF a contesto lungo e RSS. Un solo llama alla volta.
set -u
cd /workspace/strata-bench
L=/workspace/llama.cpp; B=$L/build
R=/workspace/strata-plus/traces/raw/agent_v12_pilot; mkdir -p $R
LOG=/workspace/strata-plus/traces/raw/v11/campaign.log
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
step() { local tag=$1; shift
  log "$tag precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)"
  python3 tools/cpu_foreign.py monitor $R/cpu_$tag.log 2 & local MON=$!
  log "START $tag llama_procs=$(pgrep -fc 'llama_spec_trace|llama-server|llama-cli')"
  "$@" 2> $R/$tag.err; local e=$?
  kill $MON; wait $MON 2>/dev/null
  log "END $tag exit $e cpu(intervals_ge0.5 max, escl. sand-host): $(python3 tools/cpu_judge.py $R/cpu_$tag.log)"; [ $e -eq 0 ] || { log "FAILED $tag"; exit 1; }; }
step agent_v12_build c++ -std=c++17 -O3 -DNDEBUG -DGGML_BACKEND_SHARED -DGGML_SHARED -DGGML_USE_CPU -DLLAMA_SHARED -I$L/common -I$L/vendor -I$L/include -I$L/ggml/include -I/workspace/strata-src/include proxy/llama_spec_trace_v12.cpp build-strata-cpu/libstrata_spec.a -L$B/bin -lllama-common -lllama -lggml -lggml-base -Wl,-rpath,$B/bin -o proxy/llama_spec_trace.v12.bin
BIN=./proxy/llama_spec_trace.v12.bin
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -ub 512 --no-repack --dmax 7"
echo "$BIN $FL -c 131072 -b 131072 --spec-draft-n-max 3 --mode base --prompts datasets/agent_v12_alloc.jsonl" > $R/cmds.txt
step agent_v12_pilot_alloc131k $BIN $FL -c 131072 -b 131072 --spec-draft-n-max 3 --mode base --prompts datasets/agent_v12_alloc.jsonl --tag agent_v12_pilot_alloc131k --out $R/agent_v12_pilot_alloc131k
echo "$BIN $FL -c 65536 -b 65536 --spec-draft-n-max 7 --mode tf --live-src mtp --prompts datasets/agent_v12_pilot.jsonl" >> $R/cmds.txt
step agent_v12_pilot_tf49k $BIN $FL -c 65536 -b 65536 --spec-draft-n-max 7 --mode tf --live-src mtp --prompts datasets/agent_v12_pilot.jsonl --tag agent_v12_pilot_tf49k --out $R/agent_v12_pilot_tf49k
touch $R/pilot.done; log "agent_v12 pilot.done"
