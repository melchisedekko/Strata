#!/usr/bin/env bash
# proxy CPU, non AMD. Dopo run_agent_v12.sh (runs.done): post-processing agent_v12 come run_check_v12.sh (annotate_v11, post_agent_v12,
# validate, divergence, MANIFEST + AGENT_V12_READY, file a-w); poi E4 = run_e4_v11b.sh invariato, con monitor CPU esterno.
set -u
cd /workspace/strata-bench
R=/workspace/strata-plus/traces/raw/agent_v12; V=/workspace/strata-plus/traces/agent_v12
LOG=/workspace/strata-plus/traces/raw/v11/campaign.log; O11=/workspace/strata-plus/traces/raw/v11
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
BIN=./proxy/llama_spec_trace.v12.nollamafile
while [ ! -f $R/runs.done ]; do sleep 20; done
if [ ! -f $V/AGENT_V12_READY ]; then
mkdir -p $V
(cd tools && ANN_RAW=$R ANN_OUT=$V ANN_SPLIT=agent_v12 ANN_REF_GLOB='agent_v12_tf_d7.jsonl' python3 annotate_v11.py > ../logs/annotate_agent_v12.log 2>&1) || { log "FAILED annotate agent_v12"; exit 1; }
rm -f $V/holdout_counts.json
python3 tools/post_agent_v12.py $V $R datasets/agent_v12_c49k.jsonl $BIN > logs/post_agent_v12.log 2>&1 || { log "FAILED post_agent_v12"; exit 1; }
python3 tools/agent_v12_validate.py $V > logs/agent_v12_validate.log 2>&1 || { log "FAILED agent_v12 validate: $(tail -3 logs/agent_v12_validate.log | tr '\n' ' ')"; exit 1; }
log "agent_v12 validate ok: $(head -1 logs/agent_v12_validate.log)"
python3 tools/check_v12_divergence.py $V agent_v12 $V/agent_v12_divergence.json > logs/agent_v12_divergence.log 2>&1 || { log "FAILED agent_v12 divergence"; exit 1; }
log "agent_v12 divergence: $(tr '\n' ' ' < logs/agent_v12_divergence.log | cut -c1-600)"
cp datasets/agent_v12_c49k.jsonl $V/dataset_agent_v12_c49k.jsonl; cp datasets/agent_v12_c49k_meta.json $V/dataset_agent_v12_c49k_meta.json; cp $R/cmds.txt $R/build_info.txt $V/
for f in $R/cpu_agent_v12_*.log; do cp $f $V/; done
(cd $V && for f in $(ls | grep -v MANIFEST.sha256); do sha256sum $f; done > MANIFEST.sha256 && sha256sum -c --quiet MANIFEST.sha256) || { log "FAILED agent_v12 manifest"; exit 1; }
M=$(sha256sum $V/MANIFEST.sha256 | cut -d' ' -f1)
printf '{"created":"%s","schema":"strataplus.v1.1","split":"agent_v12","label":"proxy CPU, non AMD","build":"llama_spec_trace.v12.nollamafile (GGML_LLAMAFILE=OFF) sha256 %s","ctx_limit":49152,"manifest":"%s","manifest_sha256":"%s","files":%s}\n' "$(date '+%F %T %Z')" "$(sha256sum $BIN | cut -d' ' -f1)" "$V/MANIFEST.sha256" "$M" "$(wc -l < $V/MANIFEST.sha256)" > $V/AGENT_V12_READY
chmod a-w $V/*
log "AGENT_V12_READY manifest_sha256=$M ready_sha256=$(sha256sum $V/AGENT_V12_READY | cut -d' ' -f1)"
fi
# E4
sha256sum /workspace/llama.cpp/build/bin/libllama-common.so.0.7.0 > $O11/e4_libllama_common_before.sha256
python3 tools/cpu_foreign.py monitor $O11/cpu_e4.log 2 & MON=$!
nice -n 19 bash ./run_e4_v11b.sh; e=$?
kill $MON; wait $MON 2>/dev/null
sha256sum /workspace/llama.cpp/build/bin/libllama-common.so.0.7.0 > $O11/e4_libllama_common_after.sha256
log "NOTE E4 run_e4_v11b.sh exit $e; monitor CPU complessivo $O11/cpu_e4.log: $(python3 tools/cpu_judge.py $O11/cpu_e4.log)"
