#!/usr/bin/env bash
# proxy CPU, non AMD, llama.cpp non Strata. Run (a') vs default (a) sul holdout 90, tracer v14 + arbitro proxy/strata_arbiter_v1.hpp,
# CON A/B tok/s a coppie alternate. Vale anche come A/B flag-only "--spec 8 --mtp-max-t 4" (a') contro la baseline default (a).
# v3 (27/10/2026 CET): parte da run_live_combo_aprime_holdout_v2.sh (e1140052…, NON modificato, mai lanciato). Specifica e soglie del Lead:
# runs/live_combo_aprime_holdout_v3.md (leggere prima). SCRITTO, NON LANCIATO: si lancia solo su richiesta esplicita, in una finestra annunciata.
# Dominio edit (etichetta pubblica edit_np): il tag reale dei file si legge da STRATAPLUS_EDIT_TAG (env, oppure il file locale
# ${STRATAPLUS_PRIVATE_ENV:-/workspace/lic_rm/edit_dataset.env}); ogni file per richiesta del dominio edit ha il tag nel nome; nei report solo aggregati.
# Regole: nice 19, UN solo processo llama alla volta (controllo prima di ogni passata), CPU libera (cpu_foreign wait) prima di ogni passata,
# monitor CPU 2 s, START/END in campaign.log e in cpu_busy_bench.log (via tools/bench_window_log.py se vivo, altrimenti scritti qui).
set -u
cd /workspace/strata-bench
PENV=${STRATAPLUS_PRIVATE_ENV:-/workspace/lic_rm/edit_dataset.env}
ET=${STRATAPLUS_EDIT_TAG:-$(grep -s '^STRATAPLUS_EDIT_TAG=' "$PENV" | head -1 | cut -d= -f2-)}
OUT=/workspace/strata-plus/traces/raw/aprime_holdout_v14_ab; LOG=/workspace/strata-plus/traces/raw/v11/campaign.log
BUSY=/workspace/strata-plus/cpu_busy_bench.log
BIN=./proxy/llama_spec_trace.v14.nollamafile; B=/workspace/llama.cpp/build-nollamafile
P=datasets/holdout_90.jsonl; PCC=datasets/holdout_90_codechat.jsonl; PCE=datasets/holdout_90_${ET}.jsonl
REF=/workspace/strata-plus/traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv; TF7=/workspace/strata-plus/traces/raw/v11_holdout/holdout_tf_d7.jsonl
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
[ -n "$ET" ] || { log "FAILED aprime_ab_v3: STRATAPLUS_EDIT_TAG non impostato"; exit 1; }
mkdir -p $OUT
# finestre per cpu_busy_bench.log: se il mirror tools/bench_window_log.py non e' vivo, le scrive lo script nello stesso formato
MIRROR=1; pgrep -f 'tools/bench_window_log.py' >/dev/null || MIRROR=0
win_start() { log "START $1"; [ $MIRROR = 1 ] || echo "$(date '+%F %T') | (in corso) | START $1  (strata-bench, scritto da run v3) |" >> $BUSY; WS=$(date '+%F %T'); }
win_end() { log "END $1 $2"; [ $MIRROR = 1 ] || echo "$WS | $(date '+%F %T') | $1  (strata-bench, 1 processo llama, scritto da run v3) | $2" >> $BUSY; }
# verifica degli input fissati (se uno non coincide: stop)
sha256sum -c --quiet <<SHA || { log "FAILED aprime_ab_v3: sha256 degli input diverso dal run file"; exit 1; }
e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e  $BIN
ddea7320ba99054810275d0228c89d1d0b93abd7ab0e1e5584507e739b048283  proxy/llama_spec_trace_v14.cpp
85bb5341d9995d495bd2dd72ba52349ccccbed4497eeb00da67e1b500d8e7c19  proxy/strata_arbiter_v1.hpp
2b0e8b9a0c45d6927dca09db8f352a288305f5521e0c874ff45d4c87bf46611a  proxy/strata_arbiter_v1.py
739fbb9c606c881122f1426091aa47dc7f59873176405951b2e7aa7b0febdcb3  $P
18288525fff122efc9790efbeadcbf810ae5c650149833ea5cb8a141efdba84e  $PCC
6b2404c8b4d5de552c8faf1f27dc09d2b59ceb62721d5a76f5a769c1ed2739f2  $PCE
0a86e4679f75c4a2aaf1361d7d1b742d374ac7489aae82daf93a3e349c040a9d  $REF
a16cf384f1dc5c06cbb5ae544051293413fa016fc3a1710401fad62b6ccad854  $TF7
ef3d929534cecb1c60dcb5953bb44452a75a6b91dd69cb2b09569dbde51d59f7  $B/bin/libllama-common.so.0.7.0
18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b  models/qwen35-2b-mtp-q4_k_m.gguf
349866f270653c9fdced2e8a13a6b9fe94f1f0136aeb015b8c30640acb002ef2  /workspace/strata-plus/traces/mtp_cap_prefix_check.json
42dd8621503ef07dbea6e34d1ca22791e001fed95062d7970898a81b6fc8b993  tools/mtp_cap_prefix_check.py
808ebcc95997fef256bb4f3642f5740ff2aa6c4755a3c34750c20eecaab82e3e  tools/aprime_post.py
7e1a2dcdd757421bed5939878f5647d42e792f68a5540aa0cafd3cc51eddb0fc  tools/aprime_toks_ab.py
f4276c7bcb733f7013f8b52854e010c7a456e9f029c6a950cb36eedd53fb2263  tools/cpu_foreign.py
8fb3e560689cd6784235feb2e899f63fec164a7324a2cee1e5a196459c6c027f  tools/cpu_judge.py
SHA
nollama() { pgrep -f 'llama_spec_trace|llama-cli|llama-server|llama-bench|llama-' >/dev/null && { log "FAILED aprime_ab_v3: un altro processo llama e' attivo"; exit 1; }; return 0; }
nollama
[ -f /workspace/strata-plus/traces/raw/v11/e4v14.done ] || { log "FAILED aprime_ab_v3: E4 v14 non concluso (e4v14.done assente)"; exit 1; }
# pre-check del cap: la condizione cap-prefix NON e' al 100% (5210/5389 in mtp_cap_prefix_check.json) -> si rigenera il TF a cap 3 (fase 0)
python3 -c "import json,sys; a=json.load(open('/workspace/strata-plus/traces/mtp_cap_prefix_check.json'))['all_pairs']; print(a['coincident'],a['positions_same_context'],a['all_100pct']); sys.exit(0 if a['all_100pct'] else 3)" > $OUT/cap_precheck.txt; CAP=$?
[ $CAP -eq 0 ] && log "aprime_ab_v3: cap-prefix al 100% (inatteso): la fase 0 gira comunque" || log "aprime_ab_v3: cap-prefix NON al 100% ($(cat $OUT/cap_precheck.txt)): fase 0 TF cap 3"
unset STRATA_DRAFT_VOCAB
# registrazione: comandi, hardware, versioni (prima di ogni llama)
{ echo "# proxy CPU, non AMD, llama.cpp non Strata"; date '+%F %T %Z'; uname -a; lscpu; nproc; free -m; cat /proc/loadavg
  gcc --version | head -1; cmake --version 2>/dev/null | head -1; python3 --version
  echo "llama.cpp $(git -C /workspace/llama.cpp rev-parse HEAD 2>&1) dirty_files=$(git -C /workspace/llama.cpp status --short 2>/dev/null | wc -l)"
  grep -E 'GGML_LLAMAFILE|GGML_NATIVE|CMAKE_BUILD_TYPE:' $B/CMakeCache.txt 2>/dev/null
  env | grep -E '^(STRATA|GGML|LLAMA|OMP)' | grep -v 'STRATAPLUS_EDIT' | sort
  sha256sum $BIN proxy/llama_spec_trace_v14.cpp proxy/strata_arbiter_v1.hpp proxy/strata_arbiter_v1.py $P $PCC $PCE $REF $TF7 $B/bin/lib*.so* tools/aprime_post.py tools/mtp_cap_prefix_check.py tools/aprime_toks_ab.py runs/run_live_combo_aprime_holdout_v3.sh
  ldd $BIN | grep -E 'ggml|llama'; } > $OUT/build_env_info_${ET}.txt 2>&1
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7 --spec-draft-n-max 3"
ARGS_TF="--mode tf --live-src mtp"; ARGS_A="--mode live --live-src aprime --ref $REF"; ARGS_B="--mode live --live-src default_a --ref $REF"
touch $OUT/cmds_${ET}.txt
# una passata: $1 = tag base, $2 = argomenti; gira codechat e poi edit
pass() {
 for part in codechat edit; do
  if [ $part = edit ]; then tag=${1}_${ET}; PR=$PCE; else tag=$1; PR=$PCC; fi
  [ -f $OUT/$tag.ok ] && { log "$tag gia' completato, salto"; continue; }
  nollama
  echo "nice -n 19 $BIN $FL --prompts $PR $2 --tag $tag --out $OUT/$tag" >> $OUT/cmds_${ET}.txt
  log "$tag precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)"
  python3 tools/cpu_foreign.py monitor $OUT/cpu_$tag.log 2 & MON=$!
  win_start $tag
  nice -n 19 $BIN $FL --prompts $PR $2 --tag $tag --out $OUT/$tag 2> $OUT/$tag.err; e=$?
  kill $MON; wait $MON 2>/dev/null
  win_end $tag "exit $e cpu(intervals_ge0.5 max, escl. sand-host): $(python3 tools/cpu_judge.py $OUT/cpu_$tag.log)"
  [ $e -eq 0 ] || { log "FAILED $tag"; exit 1; }; touch $OUT/$tag.ok
 done
}
# greedy (ii): un solo prompt diverso ferma tutto
gcheck() { for sfx in "" _${ET}; do fs=""; for t in "$@"; do fs="$fs $OUT/$t$sfx.jsonl"; done
  python3 tools/aprime_toks_ab.py greedy $OUT/greedy_${1}${sfx:-_codechat}.json $fs > $OUT/greedy_${1}${sfx:-_codechat}.out 2>&1 || { log "FAILED aprime_ab_v3: greedy diverso o errore ($1$sfx), STOP (regola ii)"; touch $OUT/STOPPED_greedy; exit 1; }; done; }
# fase 0: TF cap 3
pass holdout_tf_cap3_v14 "$ARGS_TF"
# fasi 1-2: coppie alternate ABBA ABBA (A = (a'), B = default (a)); coppia i = (aprime_r<i>, default_a_r<i>)
# dopo ogni passata da B:1 in poi: greedy su tutte le passate gia' fatte (output_ids identici per prompt), al primo prompt diverso STOP
DONE=""
for step in A:1 B:1 B:2 A:2 A:3 B:3 B:4 A:4; do
  arm=${step%%:*}; r=${step#*:}
  if [ $arm = A ]; then t=aprime_r$r; pass $t "$ARGS_A"; else t=default_a_r$r; pass $t "$ARGS_B"; fi
  DONE="$DONE $t"; [ $step = A:1 ] || gcheck $DONE
done
# controlli (nessun llama): validita' cand.mtp (rep 1), coerenza/AL/greedy vs ref (rep 1), A/B tok/s (4 coppie)
for sfx in "" _${ET}; do n=${sfx:-_codechat}
  nice -n 19 python3 tools/mtp_cap_prefix_check.py $OUT/validity_cand_mtp_live_vs_tf$n.json \
    $OUT/aprime_r1$sfx.jsonl:$OUT/holdout_tf_cap3_v14$sfx.jsonl $OUT/default_a_r1$sfx.jsonl:$OUT/holdout_tf_cap3_v14$sfx.jsonl \
    $OUT/aprime_r1$sfx.jsonl:$TF7 $OUT/default_a_r1$sfx.jsonl:$TF7 $OUT/holdout_tf_cap3_v14$sfx.jsonl:$TF7 > $OUT/validity$n.out 2>&1
  nice -n 19 python3 tools/aprime_post.py $OUT/aprime_post$n.json $OUT/aprime_r1$sfx.jsonl $OUT/default_a_r1$sfx.jsonl > $OUT/aprime_post$n.out 2>&1
  A=""; Bb=""; for r in 1 2 3 4; do A="$A,$OUT/aprime_r$r$sfx.jsonl"; Bb="$Bb,$OUT/default_a_r$r$sfx.jsonl"; done
  nice -n 19 python3 tools/aprime_toks_ab.py ab $OUT/toks_ab$n.json ${A#,} ${Bb#,} > $OUT/toks_ab$n.out 2>&1
done
# decisione (i)-(iv): file col tag edit perche' contiene aggregati edit; riferimento replay da POLICY_REPLAY_REF(+_SHA256), altrimenti (i) non valutabile
nice -n 19 python3 tools/aprime_toks_ab.py decide $OUT/aprime_ab_decision_${ET}.json $OUT/toks_ab_codechat.json $OUT/toks_ab_${ET}.json \
  $OUT/aprime_post_codechat.json $OUT/aprime_post_${ET}.json $OUT/validity_cand_mtp_live_vs_tf_codechat.json $OUT/validity_cand_mtp_live_vs_tf_${ET}.json > $OUT/aprime_ab_decision_${ET}.out 2>&1
(cd $OUT && sha256sum *.jsonl *.json *.txt *.err *.out cpu_*.log > MANIFEST_${ET}.sha256)
touch $OUT/aprime_ab_v3.done; log "aprime_ab_v3 runs.done (MANIFEST $(sha256sum $OUT/MANIFEST_${ET}.sha256 | cut -c1-16))"
