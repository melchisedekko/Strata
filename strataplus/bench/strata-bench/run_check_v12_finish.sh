#!/usr/bin/env bash
# Completa run_check_v12.sh dopo il fallimento di check_v12_divergence.py (header senza req_id, corretto). Nessun llama.
set -eu
cd /workspace/strata-bench
V=/workspace/strata-plus/traces/check_v12; R=/workspace/strata-plus/traces/raw/check_v12
log() { echo "$(date '+%F %T %Z') $*" >> /workspace/strata-plus/traces/raw/v11/campaign.log; }
log "NOTE check_v12 divergence fallito alle 06:39:00 (KeyError req_id sulla riga header); corretto tools/check_v12_divergence.py (salta type=header; backup .v1.py.bak), ripresa con run_check_v12_finish.sh"
rm -f $V/MANIFEST.sha256   # manifest provvisorio di annotate (includeva holdout_counts.json rimosso), mai annunciato
python3 tools/check_v12_divergence.py $V check_v12 $V/check_v12_divergence.json > logs/check_v12_divergence.log 2>&1
log "check_v12 divergence: $(tr '\n' ' ' < logs/check_v12_divergence.log)"
python3 tools/check_v12_licenses.py $V/check_v12_licenses.json > logs/check_v12_licenses.log
log "check_v12 licenses/disjoint: $(cat logs/check_v12_licenses.log)"
cp datasets/check_v12.jsonl datasets/check_v12_ids.json $R/cmds.txt $V/
(cd $V && for f in $(ls | grep -v -e MANIFEST.sha256 -e CHECK_V12_READY); do sha256sum $f; done > MANIFEST.sha256 && sha256sum -c --quiet MANIFEST.sha256)
M=$(sha256sum $V/MANIFEST.sha256 | cut -d' ' -f1)
printf '{"created":"%s","schema":"strataplus.v1.1","split":"check_v12","label":"proxy CPU, non AMD","manifest":"%s","manifest_sha256":"%s","files":%s}\n' "$(date '+%F %T %Z')" "$V/MANIFEST.sha256" "$M" "$(wc -l < $V/MANIFEST.sha256)" > $V/CHECK_V12_READY
log "CHECK_V12_READY manifest_sha256=$M ready_sha256=$(sha256sum $V/CHECK_V12_READY | cut -d' ' -f1)"
touch /workspace/strata-plus/traces/raw/v11/check_v12.done
