#!/usr/bin/env bash
# diag_greedy_aprime v1 (27/10/2026 CET). proxy CPU, non AMD, llama.cpp non Strata. Diagnosi NON temporizzata (solo identita' di output e logit).
# Stesso binario, modello e flag dei bracci della run (a') v3 (run_live_combo_aprime_holdout_v3.sh 11433cdf…, non modificato), -t 6, nice 19,
# un solo processo llama alla volta. Sottinsieme: prompt divergenti (A1/B1/TF3) + 5 identici di controllo (runs/diag_greedy_aprime_v1/prompts*.jsonl).
set -u
cd /workspace/strata-bench
ET=${STRATAPLUS_EDIT_TAG:-$(grep -s '^STRATAPLUS_EDIT_TAG=' "${STRATAPLUS_PRIVATE_ENV:-/workspace/lic_rm/edit_dataset.env}" | head -1 | cut -d= -f2-)}
[ -n "$ET" ] || exit 1
D=runs/diag_greedy_aprime_v1; BUSY=/workspace/strata-bench/cpu_busy_bench.log
BIN=./proxy/llama_spec_trace.v14.nollamafile
REF=/workspace/strata-plus/traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv; RTF3=$D/ref_tf3_all_${ET}.tsv
sha256sum -c --quiet <<SHA || { echo "sha diverso" >&2; exit 1; }
e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e  $BIN
18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b  models/qwen35-2b-mtp-q4_k_m.gguf
0a86e4679f75c4a2aaf1361d7d1b742d374ac7489aae82daf93a3e349c040a9d  $REF
ef3d929534cecb1c60dcb5953bb44452a75a6b91dd69cb2b09569dbde51d59f7  /workspace/llama.cpp/build-nollamafile/bin/libllama-common.so.0.7.0
SHA
unset STRATA_DRAFT_VOCAB
FL0="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --spec-draft-n-max 3"
nollama() { while pgrep -f 'llama_spec_trace|llama-cli|llama-server|llama-bench|llama-' >/dev/null; do sleep 10; done; }
{ date '+%F %T %Z'; uname -a; nproc; cat /proc/loadavg; echo "llama.cpp $(git -C /workspace/llama.cpp rev-parse HEAD) dirty: $(git -C /workspace/llama.cpp status --short | tr '\n' ' ')"
  grep -E 'GGML_LLAMAFILE|GGML_NATIVE|CMAKE_BUILD_TYPE:' /workspace/llama.cpp/build-nollamafile/CMakeCache.txt; ldd $BIN | grep -E 'ggml|llama'
  sha256sum $BIN /workspace/llama.cpp/build-nollamafile/bin/lib*.so* models/qwen35-2b-mtp-q4_k_m.gguf $REF $D/prompts*.jsonl $D/ref_tf3*.tsv runs/run_diag_greedy_aprime_v1.sh; } > $D/env_info_${ET}.txt 2>&1
echo "$(date '+%F %T') | (in corso) | START diag_greedy_aprime  (strata-bench, non temporizzata, build Policy in corso) |" >> $BUSY; WS=$(date '+%F %T')
run() {  # $1 tag, resto: argomenti
  local tag=$1; shift
  for part in codechat edit; do
    if [ $part = edit ]; then t=${tag}_${ET}; PR=$D/prompts_${ET}.jsonl; else t=$tag; PR=$D/prompts.jsonl; fi
    [ -f $D/$t.ok ] && continue
    nollama
    echo "$(date '+%F %T %Z') nice -n 19 $BIN $FL0 --prompts $PR $* --tag $t --out $D/$t" >> $D/cmds_${ET}.txt
    nice -n 19 $BIN $FL0 --prompts $PR "$@" --tag $t --out $D/$t 2> $D/$t.err; e=$?
    echo "$(date '+%F %T %Z') exit $e $t" >> $D/cmds_${ET}.txt
    [ $e -eq 0 ] && touch $D/$t.ok
  done
}
# (1) greedy puro batch 1, 2 volte
run base_r1 --mode base --dmax 7
run base_r2 --mode base --dmax 7
# (2) ripetibilita' dei bracci (A1 = aprime, B1 = default_a, come nello script v3)
run aprime_rr1 --mode live --live-src aprime --ref $REF --dmax 7
run aprime_rr2 --mode live --live-src aprime --ref $REF --dmax 7
run default_a_rr1 --mode live --live-src default_a --ref $REF --dmax 7
run default_a_rr2 --mode live --live-src default_a --ref $REF --dmax 7
# (3) batch di verifica fissato, senza arbitro e senza MTP: ywrong (bozza sempre rifiutata, T = dmax+1 a ogni round, 1 token/round),
#     yright (bozza = greedy TF3, T = dmax+1), e llama.cpp draft-mtp puro cap 3 (senza arbitro)
run ywrong_d3 --mode live --live-src ywrong --ref $RTF3 --dmax 3
run ywrong_d7 --mode live --live-src ywrong --ref $RTF3 --dmax 7
run yright_d7 --mode live --live-src yright --ref $RTF3 --dmax 7
run mtp_cap3 --mode live --live-src mtp --ref $REF --dmax 7
echo "$WS | $(date '+%F %T') | diag_greedy_aprime  (strata-bench, 1 processo llama, -t 6 nice 19, non temporizzata, build Policy in corso) | $(ls $D/*.ok | wc -l)/20 passate ok |" >> $BUSY
touch $D/diag.done
