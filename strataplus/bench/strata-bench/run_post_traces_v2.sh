#!/usr/bin/env bash
# v2 (03:10 CET): traces/v1.1 unica dir (tune + holdout_*.jsonl), un MANIFEST.sha256, marker V11_MANIFEST_READY.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11; TR=/workspace/strata-plus/traces; V=$TR/v1.1
while [ ! -f $OUT/holdout.done ]; do sleep 15; done
echo "$(date '+%F %T %Z') START annotate_v11 -> $V" >> $OUT/campaign.log
rm -rf $V
(cd tools && python3 annotate_v11.py > ../logs/annotate_v11.log 2>&1) || { echo "$(date '+%F %T %Z') FAILED annotate_v11" >> $OUT/campaign.log; exit 1; }
(cd $V && sha256sum -c --quiet MANIFEST.sha256) || { echo "$(date '+%F %T %Z') FAILED manifest check" >> $OUT/campaign.log; exit 1; }
M=$(sha256sum $V/MANIFEST.sha256 | cut -d' ' -f1)
printf '{"created":"%s","schema":"strataplus.v1.1","label":"proxy CPU, non AMD","manifest":"%s","manifest_sha256":"%s","files":%s,"holdout_files":%s,"cost_profile":"cost_p4_cpu.json","cost_profile_sha256":"%s"}\n' \
  "$(date '+%F %T %Z')" "$V/MANIFEST.sha256" "$M" "$(wc -l < $V/MANIFEST.sha256)" "$(grep -c '  holdout_' $V/MANIFEST.sha256)" "$(sha256sum $TR/cost_p4_cpu.json | cut -d' ' -f1)" > $TR/V11_MANIFEST_READY
echo "$(date '+%F %T %Z') V11_MANIFEST_READY manifest_sha256=$M" >> $OUT/campaign.log
python3 tools/tune_al_v11.py $TR/v11_tune_metrics.json > logs/tune_al_v11.log 2>&1
echo "$(date '+%F %T %Z') tune metrics -> $TR/v11_tune_metrics.json exit $?" >> $OUT/campaign.log
touch $OUT/manifest.done
