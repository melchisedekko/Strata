#!/usr/bin/env bash
# proxy CPU, modello denso, non AMD. P4 v1.1: parte dopo la campagna v11, con controllo ps prima e durante.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11
while [ ! -f $OUT/campaign.done ]; do sleep 15; done
CMD="--spec-type draft-mtp --spec-draft-n-max 7 -t 6 --temp 0 -n 8 -c 4096 -b 4096 -ub 512 --no-repack --prompts datasets/p4_prompts.jsonl --dmax 7 --mode p4 --p4-reps 20"
echo "./proxy/llama_spec_trace.v11.bin -m <model> $CMD --tag <tag> --out <out>" > $OUT/p4_cmd.txt
pscheck() { echo "== $(date '+%F %T %Z') $1"; ps -eo pid,pcpu,rss,etimes,args --sort=-pcpu | head -8; }
for spec in "models/qwen35-2b-mtp-q4_k_m.gguf p4_2b_q4km" "models/qwen35-2b-mtp-q8_0.gguf p4_2b_q8"; do
  set -- $spec
  # wait (max 10 min) until no other heavy process (run_v2.py or >50% CPU) is running
  for i in $(seq 1 40); do
    H=$(ps -eo pcpu,args --no-headers | awk '$1>50' | grep -v -E "ps -eo|awk" | wc -l); V=$(pgrep -fc run_v2.py)
    [ "$H" -eq 0 ] && [ "$V" -eq 0 ] && break; echo "$(date '+%T') waiting heavy=$H run_v2=$V" >> $OUT/p4_ps.log; sleep 15
  done
  pscheck "BEFORE $2" >> $OUT/p4_ps.log
  ( while true; do sleep 10; pscheck "DURING $2" >> $OUT/p4_ps.log; done ) & MON=$!
  echo "$(date '+%F %T %Z') START $2" >> $OUT/campaign.log
  ./proxy/llama_spec_trace.v11.bin -m $1 $CMD --tag $2 --out $OUT/$2 2> $OUT/$2.err
  echo "$(date '+%F %T %Z') END $2 exit $?" >> $OUT/campaign.log
  kill $MON
done
touch $OUT/p4.done
