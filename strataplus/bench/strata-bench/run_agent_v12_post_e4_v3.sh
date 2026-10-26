#!/usr/bin/env bash
# proxy CPU, non AMD. v3 = v2 + flag tempi non usabili (Lead 08:24). v2 (sostituisce run_agent_v12_post_e4.sh, steering 25/10 08:00 CET): post agent_v12 con clamp EOS in post-processing
# (tools/clamp_eos_agent_v12.py, tools/agent_v12_divergence.py), MANIFEST + AGENT_V12_READY; poi E4 con tracer v13 (run_e4_v13.sh).
set -u
cd /workspace/strata-bench
R=/workspace/strata-plus/traces/raw/agent_v12; V=/workspace/strata-plus/traces/agent_v12
LOG=/workspace/strata-plus/traces/raw/v11/campaign.log; O11=/workspace/strata-plus/traces/raw/v11
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
BIN=./proxy/llama_spec_trace.v12.nollamafile
while [ ! -f $R/runs.done ]; do sleep 20; done
if [ ! -f $V/AGENT_V12_READY ]; then
mkdir -p $V
(cd tools && ANN_RAW=$R ANN_OUT=$V ANN_SPLIT=agent_v12 ANN_REF_GLOB='agent_v12_tf_d7.jsonl' nice -n 19 python3 annotate_v11.py > ../logs/annotate_agent_v12.log 2>&1) || { log "FAILED annotate agent_v12"; exit 1; }
rm -f $V/holdout_counts.json
nice -n 19 python3 tools/post_agent_v12.py $V $R datasets/agent_v12_c49k.jsonl $BIN > logs/post_agent_v12.log 2>&1 || { log "FAILED post_agent_v12"; exit 1; }
nice -n 19 python3 tools/clamp_eos_agent_v12.py $V > logs/clamp_eos_agent_v12.log 2>&1 || { log "FAILED clamp_eos_agent_v12"; exit 1; }
cp logs/clamp_eos_agent_v12.log $V/eos_clamp_counts.json
log "agent_v12 clamp EOS (post-processing): $(cat logs/clamp_eos_agent_v12.log | cut -c1-500)"
nice -n 19 python3 tools/agent_v12_timing_flag.py $V > logs/agent_v12_timing_flag.log 2>&1 || { log "FAILED agent_v12 timing flag"; exit 1; }
cp /workspace/strata-plus/cpu_busy_policy.log $V/cpu_busy_policy_snapshot.log; cp /workspace/strata-plus/cpu_busy_bench.log $V/cpu_busy_bench_snapshot.log
nice -n 19 python3 tools/agent_v12_validate.py $V > logs/agent_v12_validate.log 2>&1 || { log "FAILED agent_v12 validate: $(tail -3 logs/agent_v12_validate.log | tr '\n' ' ')"; exit 1; }
log "agent_v12 validate ok: $(head -1 logs/agent_v12_validate.log)"
nice -n 19 python3 tools/agent_v12_divergence.py $V agent_v12 $V/agent_v12_divergence.json > logs/agent_v12_divergence.log 2>&1 || { log "FAILED agent_v12 divergence"; exit 1; }
log "agent_v12 divergence (clamped): $(tr '\n' ' ' < logs/agent_v12_divergence.log | cut -c1-600)"
cp datasets/agent_v12_c49k.jsonl $V/dataset_agent_v12_c49k.jsonl; cp datasets/agent_v12_c49k_meta.json $V/dataset_agent_v12_c49k_meta.json; cp $R/cmds.txt $R/build_info.txt $V/
cp tools/clamp_eos_agent_v12.py tools/agent_v12_divergence.py tools/agent_v12_timing_flag.py $V/
for f in $R/cpu_agent_v12_*.log; do cp $f $V/; done
(cd $V && for f in $(ls | grep -v MANIFEST.sha256); do sha256sum $f; done > MANIFEST.sha256 && sha256sum -c --quiet MANIFEST.sha256) || { log "FAILED agent_v12 manifest"; exit 1; }
M=$(sha256sum $V/MANIFEST.sha256 | cut -d' ' -f1)
printf '{"created":"%s","schema":"strataplus.v1.1","split":"agent_v12","label":"proxy CPU, non AMD","license":"MIT (Strata)","build":"llama_spec_trace.v12.nollamafile (GGML_LLAMAFILE=OFF) sha256 %s","tracer_note":"tracer v12 non corretto per i 4 modi (coerenza); committed/accepted limitati all EOS in post-processing","eos_clamp_rule":"committed = min(committed_raw, output_tokens - pos); accepted = min(accepted_raw, committed); AL di round = min(accepted+1, committed)","committed_clamped_at_eos":%s,"timing_validity":"tempi non usabili come misura (intera serie; carico CPU estraneo, vedi cpu_agent_v12_*.log e cpu_busy_policy_snapshot.log)","metrics_reported":["AL","greedy_equal_ref","first_divergence_pos"],"ctx_limit":49152,"manifest":"%s","manifest_sha256":"%s","files":%s}\n' "$(date '+%F %T %Z')" "$(sha256sum $BIN | cut -d' ' -f1)" "$(cat logs/clamp_eos_agent_v12.log)" "$V/MANIFEST.sha256" "$M" "$(wc -l < $V/MANIFEST.sha256)" > $V/AGENT_V12_READY
chmod a-w $V/*
log "AGENT_V12_READY manifest_sha256=$M ready_sha256=$(sha256sum $V/AGENT_V12_READY | cut -d' ' -f1)"
fi
# E4 con tracer v13
sha256sum /workspace/llama.cpp/build/bin/libllama-common.so.0.7.0 > $O11/e4_libllama_common_before.sha256
bash ./run_e4_v13.sh; e=$?
sha256sum /workspace/llama.cpp/build/bin/libllama-common.so.0.7.0 > $O11/e4_libllama_common_after.sha256
log "NOTE E4 run_e4_v13.sh exit $e"
