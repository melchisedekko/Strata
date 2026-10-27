#!/usr/bin/env bash
# diag_tiled_mm0 v1 (27/10/2026 CET). proxy CPU, non AMD, llama.cpp non Strata. Prova decisiva approvata da Lead alle 15:11 CET.
# Identico a aprime_rr1 / default_a_rr1 / base_r1 di run_diag_greedy_aprime_v1.sh, con la sola aggiunta di GGML_CPU_TILED_MM=0.
# Previsione pre-registrata: runs/diag_tiled_mm0_PREDICTION.md (sha 2a882b80…). Tempi NON validi (CPU condivisa).
set -u
cd /workspace/strata-bench
ET=${STRATAPLUS_EDIT_TAG:-$(grep -s '^STRATAPLUS_EDIT_TAG=' "${STRATAPLUS_PRIVATE_ENV:-/workspace/lic_rm/edit_dataset.env}" | head -1 | cut -d= -f2-)}
[ -n "$ET" ] || exit 1
D=runs/diag_greedy_aprime_v1; BUSY=/workspace/strata-bench/cpu_busy_bench.log
BIN=./proxy/llama_spec_trace.v14.nollamafile
REF=/workspace/strata-plus/traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv
sha256sum -c --quiet <<SHA || { echo "sha diverso" >&2; exit 1; }
2a882b80bb6fe49ae8051bf67b224f0ba78ab2e582c84b08a0017a670aa41df9  runs/diag_tiled_mm0_PREDICTION.md
e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e  $BIN
18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b  models/qwen35-2b-mtp-q4_k_m.gguf
0a86e4679f75c4a2aaf1361d7d1b742d374ac7489aae82daf93a3e349c040a9d  $REF
ef3d929534cecb1c60dcb5953bb44452a75a6b91dd69cb2b09569dbde51d59f7  /workspace/llama.cpp/build-nollamafile/bin/libllama-common.so.0.7.0
SHA
unset STRATA_DRAFT_VOCAB
export GGML_CPU_TILED_MM=0
FL0="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --spec-draft-n-max 3"
nollama() { while pgrep -f 'llama_spec_trace|llama-cli|llama-server|llama-bench|logit_probe' >/dev/null; do sleep 10; done; }
{ date '+%F %T %Z'; cat /proc/loadavg; env | grep GGML; sha256sum $BIN /workspace/llama.cpp/build-nollamafile/bin/lib*.so* /workspace/llama.cpp/ggml/src/ggml-cpu/tiled/tiled.cpp $0; } > $D/env_info_tm0_${ET}.txt 2>&1
echo "$(date '+%F %T') | (in corso) | START diag_tiled_mm0 GGML_CPU_TILED_MM=0 (strata-bench, non temporizzata, CPU condivisa, build Policy in corso) |" >> $BUSY; WS=$(date '+%F %T')
run() {
  local tag=$1; shift
  for part in codechat edit; do
    if [ $part = edit ]; then t=${tag}_${ET}; PR=$D/prompts_${ET}.jsonl; else t=$tag; PR=$D/prompts.jsonl; fi
    [ -f $D/$t.ok ] && continue
    nollama
    echo "$(date '+%F %T %Z') GGML_CPU_TILED_MM=$GGML_CPU_TILED_MM nice -n 19 $BIN $FL0 --prompts $PR $* --tag $t --out $D/$t" >> $D/cmds_${ET}.txt
    nice -n 19 $BIN $FL0 --prompts $PR "$@" --tag $t --out $D/$t 2> $D/$t.err; e=$?
    echo "$(date '+%F %T %Z') exit $e $t" >> $D/cmds_${ET}.txt
    [ $e -eq 0 ] && touch $D/$t.ok
  done
}
run aprime_tm0 --mode live --live-src aprime --ref $REF --dmax 7
run default_a_tm0 --mode live --live-src default_a --ref $REF --dmax 7
run base_tm0 --mode base --dmax 7
echo "$WS | $(date '+%F %T') | diag_tiled_mm0 GGML_CPU_TILED_MM=0 (1 processo llama, -t 6 nice 19, tempi non validi: CPU condivisa) | $(ls $D/*_tm0*.ok | wc -l)/6 passate ok |" >> $BUSY
touch $D/tm0.done
