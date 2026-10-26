#!/usr/bin/env bash
# proxy CPU, non AMD. check_v12: 20 prompt/dominio nuovi; tf Dmax=7 (stesso comando di holdout_tf_d7) + live mtp_k3, lookup, combo.
# In coda: dopo knee.done, prima di abl/E4. Un solo processo llama alla volta.
set -u
cd /workspace/strata-bench
R=/workspace/strata-plus/traces/raw/check_v12; V=/workspace/strata-plus/traces/check_v12; TR=/workspace/strata-plus/traces
LOG=/workspace/strata-plus/traces/raw/v11/campaign.log
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
while [ ! -f /workspace/strata-plus/traces/raw/v11/knee.done ]; do sleep 15; done
mkdir -p $R
log "START prepare_check_v12"
[ -f datasets/check_v12.jsonl ] || python3 prepare_check_v12.py > logs/prepare_check_v12.log 2>&1 || { log "FAILED prepare_check_v12"; exit 1; }
log "END prepare_check_v12 $(tail -1 logs/prepare_check_v12.log)"
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7"
P=datasets/check_v12.jsonl; BIN=./proxy/llama_spec_trace.v11.bin
: > $R/cmds.txt
run() { local tag=$1; shift
  echo "$BIN $FL $* --prompts $P --tag $tag --out $R/$tag" >> $R/cmds.txt
  log "$tag precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)"
  python3 tools/cpu_foreign.py monitor $R/cpu_$tag.log 2 & local MON=$!
  log "START $tag llama_procs=$(pgrep -fc 'llama_spec_trace|llama-server|llama-cli')"
  $BIN $FL "$@" --prompts $P --tag $tag --out $R/$tag 2> $R/$tag.err; local e=$?
  kill $MON; wait $MON 2>/dev/null
  log "END $tag exit $e foreign_max=$(awk 'BEGIN{m=0}{if($2>m)m=$2}END{print m}' $R/cpu_$tag.log) intervals_ge0.5=$(awk '$2>=0.5' $R/cpu_$tag.log | wc -l)"; [ $e -eq 0 ] || exit 1; }
run check_v12_tf_d7 --spec-draft-n-max 7 --mode tf --live-src mtp
python3 - $R/check_v12_tf_d7.jsonl $R/ref_tf.tsv <<'P'
import json,sys
o=open(sys.argv[2],'w')
for l in open(sys.argv[1]):
    j=json.loads(l)
    if j.get('type')=='request_end': o.write(j['req_id']+'\t'+','.join(map(str,j['output_ids']))+'\n')
P
run check_v12_live_mtp_k3 --spec-draft-n-max 3 --mode live --live-src mtp --ref $R/ref_tf.tsv
run check_v12_live_lookup --spec-draft-n-max 3 --mode live --live-src lookup --ref $R/ref_tf.tsv
run check_v12_live_combo --spec-draft-n-max 3 --mode live --live-src combo --ref $R/ref_tf.tsv
rm -rf $V
(cd tools && ANN_RAW=$R ANN_OUT=$V ANN_SPLIT=check_v12 ANN_REF_GLOB='check_v12_tf_d7.jsonl' python3 annotate_v11.py > ../logs/annotate_check_v12.log 2>&1) || { log "FAILED annotate check_v12"; exit 1; }
rm -f $V/holdout_counts.json
python3 tools/check_v12_validate.py $V > logs/check_v12_validate.log 2>&1 || { log "FAILED check_v12 validate: $(tail -3 logs/check_v12_validate.log | tr '\n' ' ')"; exit 1; }
log "check_v12 validate ok: $(head -1 logs/check_v12_validate.log)"
python3 tools/check_v12_divergence.py $V check_v12 $V/check_v12_divergence.json > logs/check_v12_divergence.log 2>&1 || { log "FAILED check_v12 divergence"; exit 1; }
log "check_v12 divergence: $(tr '\n' ' ' < logs/check_v12_divergence.log)"
cp datasets/check_v12.jsonl datasets/check_v12_ids.json $R/cmds.txt $V/
(cd $V && for f in $(ls | grep -v MANIFEST.sha256); do sha256sum $f; done > MANIFEST.sha256 && sha256sum -c --quiet MANIFEST.sha256) || { log "FAILED check_v12 manifest"; exit 1; }
M=$(sha256sum $V/MANIFEST.sha256 | cut -d' ' -f1)
printf '{"created":"%s","schema":"strataplus.v1.1","split":"check_v12","label":"proxy CPU, non AMD","manifest":"%s","manifest_sha256":"%s","files":%s}\n' "$(date '+%F %T %Z')" "$V/MANIFEST.sha256" "$M" "$(wc -l < $V/MANIFEST.sha256)" > $V/CHECK_V12_READY
log "CHECK_V12_READY manifest_sha256=$M"
touch /workspace/strata-plus/traces/raw/v11/check_v12.done
