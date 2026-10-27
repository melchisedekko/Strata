#!/usr/bin/env bash
# diag_tiled_mm0 full v1 (27/10/2026 CET). proxy CPU, non AMD, llama.cpp non Strata. Richiesto da previsione v2 (Lead, 15:13 CET):
# A1 (--live-src aprime) su tutti i 60 code/chat e 30 edit del holdout, con GGML_CPU_TILED_MM=0, resto identico a run_live_combo_aprime_holdout_v3.sh.
# Si confronta con il greedy puro batch 1 (TF3 = holdout_tf_cap3_v14, identico a base_r1 su 19/19 output e 2152/2152 round). Tempi NON validi.
set -u
cd /workspace/strata-bench
ET=${STRATAPLUS_EDIT_TAG:-$(grep -s '^STRATAPLUS_EDIT_TAG=' "${STRATAPLUS_PRIVATE_ENV:-/workspace/lic_rm/edit_dataset.env}" | head -1 | cut -d= -f2-)}
[ -n "$ET" ] || exit 1
D=runs/diag_greedy_aprime_v1; BUSY=/workspace/strata-bench/cpu_busy_bench.log
BIN=./proxy/llama_spec_trace.v14.nollamafile
REF=/workspace/strata-plus/traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv
sha256sum -c --quiet <<SHA || { echo "sha diverso" >&2; exit 1; }
2a882b80bb6fe49ae8051bf67b224f0ba78ab2e582c84b08a0017a670aa41df9  runs/diag_tiled_mm0_PREDICTION.md
f26643daec7b7216af2b20cf8984d885139f9d64f977c7441f78f126cc658faf  runs/diag_tiled_mm0_PREDICTION_v2.md
e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e  $BIN
18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b  models/qwen35-2b-mtp-q4_k_m.gguf
0a86e4679f75c4a2aaf1361d7d1b742d374ac7489aae82daf93a3e349c040a9d  $REF
SHA
unset STRATA_DRAFT_VOCAB GGML_CPU_TILED_MM_FORCE
export GGML_CPU_TILED_MM=0
FL0="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --spec-draft-n-max 3"
nollama() { while pgrep -f 'llama_spec_trace|llama-cli|llama-server|llama-bench|logit_probe' >/dev/null; do sleep 10; done; }
echo "$(date '+%F %T') | (in corso) | START diag_tiled_mm0_full GGML_CPU_TILED_MM=0 (strata-bench, non temporizzata, CPU condivisa) |" >> $BUSY; WS=$(date '+%F %T')
for part in codechat edit; do
  if [ $part = edit ]; then t=aprime_tm0_full_${ET}; PR=datasets/holdout_90_${ET}.jsonl; else t=aprime_tm0_full; PR=datasets/holdout_90_codechat.jsonl; fi
  [ -f $D/$t.ok ] && continue
  nollama
  echo "$(date '+%F %T %Z') GGML_CPU_TILED_MM=$GGML_CPU_TILED_MM nice -n 19 $BIN $FL0 --prompts $PR --mode live --live-src aprime --ref $REF --dmax 7 --tag $t --out $D/$t" >> $D/cmds_${ET}.txt
  nice -n 19 $BIN $FL0 --prompts $PR --mode live --live-src aprime --ref $REF --dmax 7 --tag $t --out $D/$t 2> $D/$t.err; e=$?
  echo "$(date '+%F %T %Z') exit $e $t" >> $D/cmds_${ET}.txt
  [ $e -eq 0 ] && touch $D/$t.ok
done
echo "$WS | $(date '+%F %T') | diag_tiled_mm0_full GGML_CPU_TILED_MM=0 (1 processo llama, -t 6 nice 19, tempi non validi: CPU condivisa) | $(ls $D/aprime_tm0_full*.ok | wc -l)/2 passate ok |" >> $BUSY
touch $D/tm0_full.done
