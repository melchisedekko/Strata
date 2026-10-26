#!/usr/bin/env bash
# Dopo il rerun Q4: sposta il run contaminato, rimette il rerun come p4_2b_q4km, ricalcola cost_p4_cpu.json e riscrive P4_EXTENDED_READY.
set -u
OUT=/workspace/strata-plus/traces/raw/v11; TR=/workspace/strata-plus/traces
while [ ! -f $OUT/p4q4rerun.done ]; do sleep 5; done
grep -q '"what":"verify","T":12' $OUT/p4_2b_q4km_r2.jsonl || { echo "$(date '+%F %T %Z') FAILED rerun Q4 incompleto, READY invariato" >> $OUT/campaign.log; exit 1; }
[ -f $OUT/p4.done ] || exit 1
mv $OUT/p4_2b_q4km.jsonl $OUT/p4_2b_q4km_first_contaminated.jsonl; mv $OUT/p4_2b_q4km.err $OUT/p4_2b_q4km_first_contaminated.err
cp $OUT/p4_2b_q4km_r2.jsonl $OUT/p4_2b_q4km.jsonl; cp $OUT/p4_2b_q4km_r2.err $OUT/p4_2b_q4km.err
cp $TR/cost_p4_cpu.json $TR/cost_p4_cpu.first_q4_contaminated.json
cd /workspace/strata-bench/tools && python3 cost_p4_v11.py > ../logs/cost_p4_v11_rerun.log 2>&1 || { echo "$(date '+%F %T %Z') FAILED cost rerun" >> $OUT/campaign.log; exit 1; }
S=$(sha256sum $TR/cost_p4_cpu.json | cut -d' ' -f1)
printf '{"created":"%s","file":"%s","sha256":"%s","models":["qwen35-2b-mtp-q4_k_m","qwen35-2b-mtp-q8_0"],"grid":"T=1..12, d=0..8","label":"proxy CPU, modello denso, non AMD","note":"Q4_K_M da rerun p4_2b_q4km_r2 (CPU libera, ps in raw/v11/p4_ps_q4rerun.log); sostituisce il READY precedente"}\n' "$(date '+%F %T %Z')" "$TR/cost_p4_cpu.json" "$S" > $TR/P4_EXTENDED_READY
echo "$(date '+%F %T %Z') cost_p4_cpu.json (Q4 rerun + Q8) + P4_EXTENDED_READY riscritto sha256=$S" >> $OUT/campaign.log
