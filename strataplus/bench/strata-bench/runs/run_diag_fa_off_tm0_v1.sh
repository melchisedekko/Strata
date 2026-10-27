#!/usr/bin/env bash
# diag_fa_off_tm0 v1 (27/10/2026 CET). proxy CPU, non AMD, llama.cpp non Strata. Decisione di Lead 15:16 CET, finestra diag_greedy_aprime.
# GGML_CPU_TILED_MM=0 e -fa off; resto identico ai bracci v3. A1 (aprime) e greedy puro (--mode base) su 90 prompt, B1 (default_a) sui prompt della diagnosi.
# Poi lanci brevi -v (1 prompt, -n 2) per leggere lo stato FA con e senza -fa off. Previsione: runs/diag_fa_off_tm0_PREDICTION.md (95e6e724…). Tempi NON validi.
set -u
cd /workspace/strata-bench
ET=${STRATAPLUS_EDIT_TAG:-$(grep -s '^STRATAPLUS_EDIT_TAG=' "${STRATAPLUS_PRIVATE_ENV:-/workspace/lic_rm/edit_dataset.env}" | head -1 | cut -d= -f2-)}
[ -n "$ET" ] || exit 1
D=runs/diag_greedy_aprime_v1; BUSY=/workspace/strata-bench/cpu_busy_bench.log
BIN=./proxy/llama_spec_trace.v14.nollamafile
REF=/workspace/strata-plus/traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv
sha256sum -c --quiet <<SHA || { echo "sha diverso" >&2; exit 1; }
95e6e724b060dd59c950ba8bd2f3ecfe525ac5de12d2d7a4385a6f064b362d8b  runs/diag_fa_off_tm0_PREDICTION.md
e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e  $BIN
18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b  models/qwen35-2b-mtp-q4_k_m.gguf
0a86e4679f75c4a2aaf1361d7d1b742d374ac7489aae82daf93a3e349c040a9d  $REF
SHA
unset STRATA_DRAFT_VOCAB GGML_CPU_TILED_MM_FORCE
export GGML_CPU_TILED_MM=0
FL0="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --spec-draft-n-max 3"
nollama() { while pgrep -f 'llama_spec_trace|llama-cli|llama-server|llama-bench|logit_probe' >/dev/null; do sleep 10; done; }
nollama
{ date '+%F %T %Z'; env | grep '^GGML'; echo "--- help (-fa):"; $BIN --help 2>&1 | grep -iE -- '-fa,|flash' ; sha256sum $BIN /workspace/llama.cpp/build-nollamafile/bin/lib*.so* $0; } > $D/env_info_fa0_${ET}.txt 2>&1
grep -q -- '-fa, --flash-attn' $D/env_info_fa0_${ET}.txt || { echo "-fa non accettato" >> $D/env_info_fa0_${ET}.txt; exit 2; }
echo "$(date '+%F %T') | (in corso) | START diag_fa_off_tm0 GGML_CPU_TILED_MM=0 -fa off (strata-bench, finestra diag_greedy_aprime, non temporizzata, CPU condivisa) |" >> $BUSY; WS=$(date '+%F %T')
one() {  # $1 tag, $2 prompts, resto argomenti
  local t=$1 PR=$2; shift 2
  [ -f $D/$t.ok ] && return
  nollama
  echo "$(date '+%F %T %Z') GGML_CPU_TILED_MM=$GGML_CPU_TILED_MM nice -n 19 $BIN $FL0 -fa off --prompts $PR $* --tag $t --out $D/$t" >> $D/cmds_${ET}.txt
  nice -n 19 $BIN $FL0 -fa off --prompts $PR "$@" --tag $t --out $D/$t 2> $D/$t.err; e=$?
  echo "$(date '+%F %T %Z') exit $e $t" >> $D/cmds_${ET}.txt
  [ $e -eq 0 ] && touch $D/$t.ok
}
one aprime_fa0 datasets/holdout_90_codechat.jsonl --mode live --live-src aprime --ref $REF --dmax 7
one aprime_fa0_${ET} datasets/holdout_90_${ET}.jsonl --mode live --live-src aprime --ref $REF --dmax 7
one default_a_fa0 $D/prompts.jsonl --mode live --live-src default_a --ref $REF --dmax 7
one default_a_fa0_${ET} $D/prompts_${ET}.jsonl --mode live --live-src default_a --ref $REF --dmax 7
one base_fa0 datasets/holdout_90_codechat.jsonl --mode base --dmax 7
one base_fa0_${ET} datasets/holdout_90_${ET}.jsonl --mode base --dmax 7
# stato FA: lanci brevi -v, 1 prompt code/chat, dopo la fine delle run (mai in parallelo)
for cfg in default fa_off; do
  nollama; X=""; [ $cfg = fa_off ] && X="-fa off"
  echo "$(date '+%F %T %Z') GGML_CPU_TILED_MM=$GGML_CPU_TILED_MM nice -n 19 $BIN ${FL0/-n 128/-n 2} $X -v --prompts $D/prompts.jsonl --limit 1 --mode base --dmax 7 --tag fa_probe_$cfg --out /tmp/dg/fa_probe_$cfg" >> $D/cmds_${ET}.txt
  nice -n 19 $BIN ${FL0/-n 128/-n 2} $X -v --prompts $D/prompts.jsonl --limit 1 --mode base --dmax 7 --tag fa_probe_$cfg --out /tmp/dg/fa_probe_$cfg > $D/fa_probe_$cfg.log 2>&1
  echo "$(date '+%F %T %Z') exit $? fa_probe_$cfg" >> $D/cmds_${ET}.txt
done
echo "$WS | $(date '+%F %T') | diag_fa_off_tm0 GGML_CPU_TILED_MM=0 -fa off (1 processo llama, -t 6 nice 19, tempi non validi: CPU condivisa) | $(ls $D/*_fa0*.ok | wc -l)/6 passate ok |" >> $BUSY
touch $D/fa0.done
