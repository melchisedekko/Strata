#!/usr/bin/env bash
# proxy CPU, modello denso, non AMD. P4 esteso v1.1: griglia T=1..12, d=0..8 (d=0 = nessun passo MTP). ps prima e durante.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11; TR=/workspace/strata-plus/traces
BIN=./proxy/llama_spec_trace.v11p4.bin
CMD="--spec-type draft-mtp --spec-draft-n-max 8 -t 6 --temp 0 -n 8 -c 4096 -b 4096 -ub 512 --no-repack --prompts datasets/p4_prompts.jsonl --dmax 7 --mode p4 --p4-reps 20 --p4-tmax 12 --p4-dmax 8"
echo "$BIN -m <model> $CMD --tag <tag> --out <out>" > $OUT/p4_cmd.txt
pscheck() { echo "== $(date '+%F %T %Z') $1"; ps -eo pid,pcpu,rss,etimes,args --sort=-pcpu | head -8; }
ready() { S=$(sha256sum $TR/cost_p4_cpu.json | cut -d' ' -f1)
  printf '{"created":"%s","file":"%s","sha256":"%s","models":%s,"grid":"T=1..12, d=0..8","label":"proxy CPU, modello denso, non AMD"}\n' \
   "$(date '+%F %T %Z')" "$TR/cost_p4_cpu.json" "$S" "$1" > $TR/P4_EXTENDED_READY; }
for spec in "models/qwen35-2b-mtp-q4_k_m.gguf p4_2b_q4km" "models/qwen35-2b-mtp-q8_0.gguf p4_2b_q8"; do
  set -- $spec
  for i in $(seq 1 40); do
    H=$(ps -eo pcpu,args --no-headers | awk '$1>50' | grep -v -E "ps -eo|awk" | wc -l); V=$(pgrep -fc run_v2.py)
    [ "$H" -eq 0 ] && [ "$V" -eq 0 ] && break; echo "$(date '+%T') waiting heavy=$H run_v2=$V" >> $OUT/p4_ps.log; sleep 15
  done
  pscheck "BEFORE $2" >> $OUT/p4_ps.log
  ( while true; do sleep 10; pscheck "DURING $2" >> $OUT/p4_ps.log; done ) & MON=$!
  echo "$(date '+%F %T %Z') START $2 (P4 esteso)" >> $OUT/campaign.log
  $BIN -m $1 $CMD --tag $2 --out $OUT/$2 2> $OUT/$2.err
  echo "$(date '+%F %T %Z') END $2 exit $?" >> $OUT/campaign.log
  kill $MON
  if ! grep -q '"what":"verify","T":12' $OUT/$2.jsonl || ! (cd tools && python3 cost_p4_v11.py > ../logs/cost_p4_v11_$2.log 2>&1); then
    echo "$(date '+%F %T %Z') FAILED $2 (nessun READY)" >> $OUT/campaign.log; exit 1; fi
  if [ $2 = p4_2b_q4km ]; then ready '["qwen35-2b-mtp-q4_k_m"]'; else ready '["qwen35-2b-mtp-q4_k_m","qwen35-2b-mtp-q8_0"]'; fi
  echo "$(date '+%F %T %Z') cost_p4_cpu.json + P4_EXTENDED_READY after $2" >> $OUT/campaign.log
done
touch $OUT/p4.done
