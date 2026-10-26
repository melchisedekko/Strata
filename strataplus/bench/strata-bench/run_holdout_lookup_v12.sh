#!/usr/bin/env bash
# proxy CPU, non AMD. holdout_lookup_v12: live lookup-only (Strata SuffixDrafter(3,64), propose(max_k=--dmax)) sui 90 prompt holdout v1.1,
# stessi flag di holdout_tf_d7 (-n 128 -c 8192 -b 8192 -ub 512 -t 6 --temp 0 --no-repack, build LLAMAFILE ON v11.bin), n_max 7, 12 e 16 via --dmax
# (per lookup-only il draft e' lbuf[0:min(lk, token rimasti)], lk=sfx.propose(dmax,..); n_rs_seq=max(--spec-draft-n-max,dmax)).
# Ref greedy = output di holdout_tf_d7 (T=1 greedy proprio). Un solo llama alla volta, pre-check CPU, monitor 2 s.
set -u
cd /workspace/strata-bench
R=/workspace/strata-plus/traces/raw/holdout_lookup_v12; mkdir -p $R
LOG=/workspace/strata-plus/traces/raw/v11/campaign.log
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
BIN=./proxy/llama_spec_trace.v11.bin
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --spec-draft-n-max 3 --mode live --live-src lookup"
P=datasets/holdout_90.jsonl
python3 -c "
import json
o=open('$R/ref_holdout_tf.tsv','w')
for l in open('/workspace/strata-plus/traces/raw/v11_holdout/holdout_tf_d7.jsonl'):
    j=json.loads(l)
    if j['type']=='request_end': o.write(j['req_id']+'\t'+','.join(map(str,j['output_ids']))+'\n')"
: > $R/cmds.txt
for n in 7 12 16; do tag=holdout_lookup_v12_n$n
  echo "$BIN $FL --dmax $n --ref $R/ref_holdout_tf.tsv --prompts $P --tag $tag --out $R/$tag" >> $R/cmds.txt
  log "$tag precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)"
  python3 tools/cpu_foreign.py monitor $R/cpu_$tag.log 2 & MON=$!
  log "START $tag"
  $BIN $FL --dmax $n --ref $R/ref_holdout_tf.tsv --prompts $P --tag $tag --out $R/$tag 2> $R/$tag.err; e=$?
  kill $MON; wait $MON 2>/dev/null
  log "END $tag exit $e cpu(intervals_ge0.5 max, escl. sand-host): $(python3 tools/cpu_judge.py $R/cpu_$tag.log)"; [ $e -eq 0 ] || { log "FAILED $tag"; exit 1; }
done
touch $R/runs.done; log "holdout_lookup_v12 runs.done"
