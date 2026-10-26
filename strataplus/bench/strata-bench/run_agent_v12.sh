#!/usr/bin/env bash
# proxy CPU, non AMD. agent_v12: 23 turni reali agent_turns_bench (Strata 7dd5cf18), ctx 49152 con troncamento dalle coppie tool piu' vecchie
# (datasets/agent_v12_c49k.jsonl, tools/prepare_agent_v12_trunc.py). Build NUOVO proxy v12 LLAMAFILE OFF (libs build-nollamafile).
# 4 modi come check_v12: tf_d7, live mtp_k3, lookup, combo (--dmax 7, --ref dal tf). nice -n 19, un solo llama alla volta, pre-check CPU.
set -u
cd /workspace/strata-bench
L=/workspace/llama.cpp; B=$L/build-nollamafile
R=/workspace/strata-plus/traces/raw/agent_v12; mkdir -p $R
LOG=/workspace/strata-plus/traces/raw/v11/campaign.log
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
step() { local tag=$1; shift
  log "$tag precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)"
  python3 tools/cpu_foreign.py monitor $R/cpu_$tag.log 2 & local MON=$!
  log "START $tag"
  nice -n 19 "$@" 2> $R/$tag.err; local e=$?
  kill $MON; wait $MON 2>/dev/null
  log "END $tag exit $e cpu(intervals_ge0.5 max, escl. sand-host): $(python3 tools/cpu_judge.py $R/cpu_$tag.log)"; [ $e -eq 0 ] || { log "FAILED $tag"; exit 1; }; }
BIN=./proxy/llama_spec_trace.v12.nollamafile
if [ ! -x $BIN ]; then
step agent_v12_build_nollamafile c++ -std=c++17 -O3 -DNDEBUG -DGGML_BACKEND_SHARED -DGGML_SHARED -DGGML_USE_CPU -DLLAMA_SHARED -I$L/common -I$L/vendor -I$L/include -I$L/ggml/include -I/workspace/strata-src/include proxy/llama_spec_trace_v12.cpp build-strata-cpu/libstrata_spec.a -L$B/bin -lllama-common -lllama -lggml -lggml-base -Wl,-rpath,$B/bin -o $BIN
fi
{ sha256sum $BIN proxy/llama_spec_trace_v12.cpp; ldd $BIN | grep -E 'ggml|llama'; grep -E 'GGML_LLAMAFILE' $B/CMakeCache.txt; } > $R/build_info.txt
log "agent_v12 bin $(sha256sum $BIN | cut -c1-16) $(ldd $BIN | grep -c build-nollamafile) libs da build-nollamafile"
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 49152 -b 49152 -ub 512 --no-repack --dmax 7"
P=datasets/agent_v12_c49k.jsonl
: > $R/cmds.txt
run() { local tag=$1; shift; echo "nice -n 19 $BIN $FL $* --prompts $P --tag $tag --out $R/$tag" >> $R/cmds.txt
  [ -f $R/$tag.ok ] && { log "$tag gia' completato, salto"; return; }
  step $tag $BIN $FL "$@" --prompts $P --tag $tag --out $R/$tag; touch $R/$tag.ok; }
run agent_v12_tf_d7 --spec-draft-n-max 7 --mode tf --live-src mtp
[ -f $R/ref_tf.tsv ] || python3 -c "
import json
o=open('$R/ref_tf.tsv','w')
for l in open('$R/agent_v12_tf_d7.jsonl'):
    j=json.loads(l)
    if j['type']=='request_end': o.write(j['req_id']+'\t'+','.join(map(str,j['output_ids']))+'\n')"
run agent_v12_live_mtp_k3 --spec-draft-n-max 3 --mode live --live-src mtp --ref $R/ref_tf.tsv
run agent_v12_live_lookup --spec-draft-n-max 3 --mode live --live-src lookup --ref $R/ref_tf.tsv
run agent_v12_live_combo --spec-draft-n-max 3 --mode live --live-src combo --ref $R/ref_tf.tsv
touch $R/runs.done; log "agent_v12 runs.done"
