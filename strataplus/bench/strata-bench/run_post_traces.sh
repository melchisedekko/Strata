#!/usr/bin/env bash
# Dopo tracce v1.1 + holdout: annotate -> MANIFEST.sha256 (tune e holdout separati) -> marker TRACES_V11_READY.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11; TR=/workspace/strata-plus/traces
while [ ! -f $OUT/holdout.done ]; do sleep 15; done
echo "$(date '+%F %T %Z') START annotate_v11" >> $OUT/campaign.log
(cd tools && python3 annotate_v11.py > ../logs/annotate_v11.log 2>&1) || { echo "$(date '+%F %T %Z') FAILED annotate_v11" >> $OUT/campaign.log; exit 1; }
(cd $TR/v11 && sha256sum -c --quiet MANIFEST.sha256) && (cd $TR/v11_holdout && sha256sum -c --quiet MANIFEST.sha256) || { echo "$(date '+%F %T %Z') FAILED manifest check" >> $OUT/campaign.log; exit 1; }
A=$(sha256sum $TR/v11/MANIFEST.sha256 | cut -d' ' -f1); H=$(sha256sum $TR/v11_holdout/MANIFEST.sha256 | cut -d' ' -f1)
printf '{"created":"%s","schema":"strataplus.v1.1","label":"proxy CPU, non AMD","tune_manifest":"%s","tune_manifest_sha256":"%s","holdout_manifest":"%s","holdout_manifest_sha256":"%s","cost_profile":"cost_p4_cpu.json","cost_profile_sha256":"%s"}\n' \
  "$(date '+%F %T %Z')" "$TR/v11/MANIFEST.sha256" "$A" "$TR/v11_holdout/MANIFEST.sha256" "$H" "$(sha256sum $TR/cost_p4_cpu.json | cut -d' ' -f1)" > $TR/TRACES_V11_READY
echo "$(date '+%F %T %Z') TRACES_V11_READY tune=$A holdout=$H" >> $OUT/campaign.log
touch $OUT/manifest.done
