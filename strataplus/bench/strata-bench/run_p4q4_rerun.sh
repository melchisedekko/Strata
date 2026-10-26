#!/usr/bin/env bash
# proxy CPU, modello denso, non AMD. Rerun P4 esteso Q4_K_M: il primo run (02:02-02:05 CET) ha avuto processi di altri agenti
# a ~100% di un core in ~9/23 snapshot. Rerun solo con CPU libera (3 check consecutivi a 5 s senza processi estranei >50%).
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11; TR=/workspace/strata-plus/traces
BIN=./proxy/llama_spec_trace.v11p4.bin
CMD="--spec-type draft-mtp --spec-draft-n-max 8 -t 6 --temp 0 -n 8 -c 4096 -b 4096 -ub 512 --no-repack --prompts datasets/p4_prompts.jsonl --dmax 7 --mode p4 --p4-reps 20 --p4-tmax 12 --p4-dmax 8"
L=$OUT/p4_ps_q4rerun.log
heavy() { ps -eo pcpu,args --no-headers | awk '$1>50' | grep -v -E "ps -eo|awk|llama_spec_trace" | wc -l; }
pscheck() { echo "== $(date '+%F %T %Z') $1"; ps -eo pid,pcpu,rss,etimes,args --sort=-pcpu | head -8; }
while [ ! -f $OUT/p4.done ]; do sleep 10; done
ok=0; for i in $(seq 1 240); do
  if [ "$(heavy)" -eq 0 ] && [ "$(pgrep -fc run_v2.py)" -eq 0 ]; then ok=$((ok+1)); else ok=0; echo "$(date '+%T') busy" >> $L; fi
  [ $ok -ge 3 ] && break; sleep 5; done
pscheck "BEFORE p4_2b_q4km_r2 (ok=$ok)" >> $L
( while true; do sleep 5; pscheck "DURING p4_2b_q4km_r2" >> $L; done ) & MON=$!
echo "$(date '+%F %T %Z') START p4_2b_q4km_r2 (rerun Q4 con CPU libera)" >> $OUT/campaign.log
$BIN -m models/qwen35-2b-mtp-q4_k_m.gguf $CMD --tag p4_2b_q4km --out $OUT/p4_2b_q4km_r2 2> $OUT/p4_2b_q4km_r2.err
echo "$(date '+%F %T %Z') END p4_2b_q4km_r2 exit $?" >> $OUT/campaign.log
kill $MON
touch $OUT/p4q4rerun.done
