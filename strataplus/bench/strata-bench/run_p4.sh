#!/usr/bin/env bash
# proxy CPU, modello denso, non AMD. Profilo P4: parte dopo la campagna tracce (niente sovrapposizione di carico).
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw
while [ ! -f $OUT/campaign.done ]; do sleep 20; done
python3 - <<'PY'
import json
ids = {'code': [], 'chat': [], 'edit': []}
with open('datasets/p4_prompts.jsonl', 'w') as f:
    for l in open('datasets/proxy_30.jsonl'):
        j = json.loads(l)
        if len(ids[j['category']]) < 2:
            ids[j['category']].append(j['id']); f.write(l)
PY
CMD="--spec-type draft-mtp --spec-draft-n-max 7 -t 6 --temp 0 -n 8 -c 4096 -b 4096 -ub 512 --no-repack --prompts datasets/p4_prompts.jsonl --dmax 7 --mode p4 --p4-reps 20"
echo "./proxy/llama_spec_trace -m <model> $CMD --tag <tag> --out <out>" > $OUT/p4_cmd.txt
for spec in "models/qwen35-2b-mtp-q4_k_m.gguf p4_2b_q4km" "models/qwen35-0.8b-mtp-q4_k_m.gguf p4_08b_q4km" "models/qwen35-0.8b-mtp-q8_0.gguf p4_08b_q8"; do
  set -- $spec
  [ -f $1 ] || continue
  echo "$(date '+%F %T %Z') START $2" >> $OUT/campaign.log
  ./proxy/llama_spec_trace -m $1 $CMD --tag $2 --out $OUT/$2 2> $OUT/$2.err
  echo "$(date '+%F %T %Z') END $2 exit $?" >> $OUT/campaign.log
done
touch $OUT/p4.done
