#!/usr/bin/env bash
# proxy CPU, non AMD. Run (a') vs default (a) sul holdout 90 con tracer v14 + arbitro proxy/strata_arbiter_v1.hpp.
# v2 (26/10 19:4x CET): sostituisce run_live_combo_aprime_holdout.sh (5066b06a…, non lanciato). Unica modifica: REGOLA edit_np,
# cioè ogni artefatto nuovo derivato dal dominio edit/edit_np ha 'edit_np' nel nome (esclusione dal sync); i report hanno solo aggregati per dominio.
# Ogni braccio gira in due passate (code+chat, poi edit_np) con lo stesso ordine del file holdout_90 (la loro concatenazione è identica byte per byte,
# sha 739fbb9c…) e l'arbitro si resetta a ogni prompt.
# Specifica: runs/live_combo_aprime_holdout_v2.md (leggere prima). SCRITTO, NON LANCIATO: lanciarlo solo su richiesta esplicita.
# Regole: nice 19, un solo processo llama alla volta (rifiuta se un altro llama_spec_trace/llama-* gira), pre-check CPU libera, monitor CPU 2 s,
# finestre START/END in campaign.log (-> cpu_busy_bench.log via tools/bench_window_log.py). Nessun dato copiato: prompt e ref per percorso.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/aprime_holdout_v14; LOG=/workspace/strata-plus/traces/raw/v11/campaign.log
BIN=./proxy/llama_spec_trace.v14.nollamafile; B=/workspace/llama.cpp/build-nollamafile
P=datasets/holdout_90.jsonl; PCC=datasets/holdout_90_codechat.jsonl; PCE=datasets/holdout_90_edit_np.jsonl; REF=/workspace/strata-plus/traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv
TF7=/workspace/strata-plus/traces/raw/v11_holdout/holdout_tf_d7.jsonl
mkdir -p $OUT
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
# verifica degli input fissati nel run file (se uno non coincide: stop)
sha256sum -c --quiet <<SHA || { log "FAILED aprime_holdout: sha256 degli input diverso dal run file"; exit 1; }
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
SHA
pgrep -f 'llama_spec_trace|llama-cli|llama-server|llama-bench' >/dev/null && { log "FAILED aprime_holdout: un altro processo llama e' attivo"; exit 1; }
[ -f /workspace/strata-plus/traces/raw/v11/e4v14.done ] || { log "FAILED aprime_holdout: E4 v14 non concluso (e4v14.done assente)"; exit 1; }
unset STRATA_DRAFT_VOCAB
{ date '+%F %T %Z'; env | grep -E '^(STRATA|GGML|LLAMA|OMP)' | sort; sha256sum $BIN proxy/llama_spec_trace_v14.cpp proxy/strata_arbiter_v1.hpp proxy/strata_arbiter_v1.py $P $PCC $PCE $REF $TF7 $B/bin/lib*.so* tools/aprime_post.py tools/mtp_cap_prefix_check.py; ldd $BIN | grep -E 'ggml|llama'; } > $OUT/build_env_info.txt
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7 --spec-draft-n-max 3"
: > $OUT/cmds.txt
# ordine fisso: (0) TF cap 3 (condizione cap-prefix non al 100%, traces/mtp_cap_prefix_check.json), (1) (a'), (2) default (a)
for spec in "holdout_tf_cap3_v14:--mode tf --live-src mtp" "aprime_holdout_v14:--mode live --live-src aprime --ref $REF" "default_a_holdout_v14:--mode live --live-src default_a --ref $REF"; do
 for part in codechat edit_np; do
  base=${spec%%:*}; args=${spec#*:}
  if [ $part = edit_np ]; then tag=${base}_edit_np; PR=$PCE; else tag=$base; PR=$PCC; fi
  [ -f $OUT/$tag.ok ] && { log "$tag gia' completato, salto"; continue; }
  echo "nice -n 19 $BIN $FL --prompts $PR $args --tag $tag --out $OUT/$tag" >> $OUT/cmds.txt
  log "$tag precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)"
  python3 tools/cpu_foreign.py monitor $OUT/cpu_$tag.log 2 & MON=$!
  log "START $tag"
  nice -n 19 $BIN $FL --prompts $PR $args --tag $tag --out $OUT/$tag 2> $OUT/$tag.err; e=$?
  kill $MON; wait $MON 2>/dev/null
  log "END $tag exit $e cpu(intervals_ge0.5 max, escl. sand-host): $(python3 tools/cpu_judge.py $OUT/cpu_$tag.log)"
  [ $e -eq 0 ] || { log "FAILED $tag"; exit 1; }; touch $OUT/$tag.ok
 done
done
# controlli (nessun llama): validita' cand.mtp live vs TF (cap 3 rigenerato e primi 3 del TF cap 7), coerenza, AL, greedy
# file per richiesta del dominio edit: sempre *_edit_np*; nei log/report solo aggregati per dominio
for sfx in "" _edit_np; do
  nice -n 19 python3 tools/mtp_cap_prefix_check.py $OUT/validity_cand_mtp_live_vs_tf$sfx.json \
    $OUT/aprime_holdout_v14$sfx.jsonl:$OUT/holdout_tf_cap3_v14$sfx.jsonl $OUT/default_a_holdout_v14$sfx.jsonl:$OUT/holdout_tf_cap3_v14$sfx.jsonl \
    $OUT/aprime_holdout_v14$sfx.jsonl:$TF7 $OUT/default_a_holdout_v14$sfx.jsonl:$TF7 $OUT/holdout_tf_cap3_v14$sfx.jsonl:$TF7 > $OUT/validity$sfx.out
  nice -n 19 python3 tools/aprime_post.py $OUT/aprime_post$sfx.json $OUT/aprime_holdout_v14$sfx.jsonl $OUT/default_a_holdout_v14$sfx.jsonl > $OUT/aprime_post$sfx.out
done
(cd $OUT && sha256sum *.jsonl *.json *.txt *.err *.out cpu_*.log > MANIFEST.sha256)
touch $OUT/aprime_holdout.done; log "aprime_holdout runs.done (MANIFEST $(sha256sum $OUT/MANIFEST.sha256 | cut -c1-16))"
