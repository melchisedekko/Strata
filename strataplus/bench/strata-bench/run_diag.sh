#!/usr/bin/env bash
# proxy CPU, non numeri AMD. Diagnostica uguaglianza greedy (dopo P4): draft = y (sempre accettato, T=8)
# oppure y spostato di un id (sempre rifiutato, T=8, rollback completo ogni round). Nessun MTP.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw
while [ ! -f $OUT/p4.done ]; do sleep 20; done
python3 - <<'PY'
import json
ref = {}
for l in open('/workspace/strata-plus/traces/raw/base_r0.jsonl'):
    j = json.loads(l)
    if j['type'] == 'request': ref[j['req_id']] = j['output_ids']
with open('datasets/diag_ref.tsv', 'w') as f:
    for k, v in ref.items(): f.write(k + '\t' + ','.join(map(str, v)) + '\n')
n = {'code': 0, 'chat': 0, 'edit': 0}
with open('datasets/diag_prompts.jsonl', 'w') as f:
    for l in open('datasets/proxy_30.jsonl'):
        j = json.loads(l)
        if n[j['category']] < 4: n[j['category']] += 1; f.write(l)
PY
COMMON="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp -t 6 --temp 0 -n 128 -c 4096 -b 4096 -ub 512 --no-repack --prompts datasets/diag_prompts.jsonl --dmax 7 --ref datasets/diag_ref.tsv"
for src in yright ywrong; do
  echo "$(date '+%F %T %Z') START diag_$src" >> $OUT/campaign.log
  ./proxy/llama_spec_trace.new $COMMON --mode live --live-src $src --tag diag_$src --out $OUT/diag_$src 2> $OUT/diag_$src.err
  echo "$(date '+%F %T %Z') END diag_$src exit $?" >> $OUT/campaign.log
done
touch $OUT/diag.done
