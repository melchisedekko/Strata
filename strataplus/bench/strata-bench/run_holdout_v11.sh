#!/usr/bin/env bash
# proxy CPU, non AMD. Holdout v1.1 (90 prompt, split=holdout): priorita' teacher-forced Dmax=7 (+lookup); live solo se resta tempo.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11
HO=/workspace/strata-plus/traces/raw/v11_holdout; mkdir -p $HO
while [ ! -f $OUT/p4.done ]; do sleep 15; done
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7"
log() { echo "$(date '+%F %T %Z') $*" >> $OUT/campaign.log; }
log "START holdout_tf_d7 ps_heavy=$(ps -eo comm,args | grep -E 'run_v2|python3 .*sim' | grep -vc grep)"
./proxy/llama_spec_trace.v11.bin $FL --spec-draft-n-max 7 --prompts datasets/holdout_90.jsonl --mode tf --live-src mtp --tag holdout_tf_d7 --out $HO/holdout_tf_d7 2> $HO/holdout_tf_d7.err
log "END holdout_tf_d7 exit $?"
touch $OUT/holdout.done
