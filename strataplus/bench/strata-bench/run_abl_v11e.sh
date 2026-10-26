#!/usr/bin/env bash
# proxy CPU, non AMD. Ripresa abl dopo kill di run_abl_v11c.sh (06:41): attende che il llama orfano abl_llamafile_on_base (PID 337045) finisca,
# poi esegue solo le parti mancanti, ciascuna con pre-check CPU (<0.5 core estranei per 30 s, escl. sand-host) e monitor 2 s. Un solo llama alla volta.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11; LOG=$OUT/campaign.log
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
pre() { log "$1 precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)"; }
while kill -0 337045 2>/dev/null; do sleep 5; done
NP=$(wc -l < datasets/diag_prompts.jsonl)
# completo = jsonl presente, err con riga finale g9_violations, e request_end + prompt saltati (>512 token, voluto ctx<512) = NP
complete() { [ -f $1.jsonl ] && grep -q '^g9_violations=' $1.err && [ $(( $(grep -c '"type": *"request_end"' $1.jsonl) + $(grep -c '^skip ' $1.err) )) -eq "$NP" ]; }
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 512 -b 512 -ub 512 --no-repack --spec-draft-n-max 3 --prompts datasets/diag_prompts.jsonl"
mkref() { python3 -c "
import json,sys
o=open(sys.argv[2],'w')
for l in open(sys.argv[1]):
    j=json.loads(l)
    if j['type']=='request_end': o.write(j['req_id']+'\t'+','.join(map(str,j['output_ids']))+'\n')" $1 $2; }
if complete $OUT/abl_llamafile_on_base; then log "END abl_llamafile_on_base (llama orfano PID 337045, avviato 06:41:21 senza pre-check da run_abl_v11c.sh; test di identita', insensibile al timing) request_end=$(grep -c request_end $OUT/abl_llamafile_on_base.jsonl), skip>512tok=$(grep -c '^skip ' $OUT/abl_llamafile_on_base.err)"
else log "abl_llamafile_on_base incompleto: spostato in invalid_abl/ e rifatto"; mkdir -p $OUT/invalid_abl; mv $OUT/abl_llamafile_on_base.* $OUT/invalid_abl/; fi
ok=1
for v in llamafile_on:./proxy/llama_spec_trace.v11.bin llamafile_off:./proxy/llama_spec_trace.v11.nollamafile; do
  n=${v%%:*}; BIN=${v#*:}
  [ -f $OUT/abl_${n}.ldd ] || ldd $BIN | grep ggml-cpu > $OUT/abl_${n}.ldd
  for step in base ywrong_T2; do t=abl_${n}_$step
    if complete $OUT/$t; then [ $step = base ] && [ ! -f $OUT/abl_${n}_ref.tsv ] && mkref $OUT/abl_${n}_base.jsonl $OUT/abl_${n}_ref.tsv; continue; fi
    pre $t; python3 tools/cpu_foreign.py monitor $OUT/cpu_$t.log 2 & MON=$!
    log "START $t"
    if [ $step = base ]; then $BIN $FL --mode base --dmax 1 --tag $t --out $OUT/$t 2> $OUT/$t.err; e=$?
    else $BIN $FL --mode live --live-src ywrong --dmax 1 --ref $OUT/abl_${n}_ref.tsv --tag $t --out $OUT/$t 2> $OUT/$t.err; e=$?; fi
    kill $MON; wait $MON 2>/dev/null
    log "END $t exit $e cpu(intervals_ge0.5 max, escl. sand-host): $(python3 tools/cpu_judge.py $OUT/cpu_$t.log)"
    [ $e -eq 0 ] && complete $OUT/$t || ok=0
    [ $step = base ] && [ ! -f $OUT/abl_${n}_ref.tsv ] && mkref $OUT/abl_${n}_base.jsonl $OUT/abl_${n}_ref.tsv
  done
done
if [ $ok -eq 1 ]; then touch $OUT/abl.done; log "abl.done"; else log "abl incompleto: abl.done NON creato"; fi
