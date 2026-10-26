#!/usr/bin/env bash
# proxy CPU, non AMD. E4: draft vocab ridotto di Strata applicato al draft MTP (mascheramento logit = argmax sulle righe del sottoinsieme).
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11
while [ ! -f $OUT/abl.done ]; do sleep 15; done
echo "$(date '+%F %T %Z') START rebuild_llama_common_e4" >> $OUT/campaign.log
ninja -C /workspace/llama.cpp/build -j 6 llama-common > logs/llama_common_rebuild_e4.log 2>&1
echo "$(date '+%F %T %Z') END rebuild_llama_common_e4 exit $?" >> $OUT/campaign.log
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7 --spec-draft-n-max 7 --prompts datasets/proxy_30.jsonl --mode tf --live-src mtp"
for v in full: dvocab:/workspace/strata-src/data/draft_vocab.bin dvocab_en:/workspace/strata-src/data/draft_vocab_en.bin; do
  n=${v%%:*}; f=${v#*:}
  echo "$(date '+%F %T %Z') START e4_tf_d7_p30_$n" >> $OUT/campaign.log
  if [ -n "$f" ]; then export STRATA_DRAFT_VOCAB=$f; else unset STRATA_DRAFT_VOCAB; fi
  ./proxy/llama_spec_trace.v11.bin $FL --tag e4_tf_d7_p30_$n --out $OUT/e4_tf_d7_p30_$n 2> $OUT/e4_tf_d7_p30_$n.err
  echo "$(date '+%F %T %Z') END e4_tf_d7_p30_$n exit $?" >> $OUT/campaign.log
done
touch $OUT/e4.done
