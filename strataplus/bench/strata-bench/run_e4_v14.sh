#!/usr/bin/env bash
# proxy CPU, non AMD. E4 con tracer v14 (= run_e4_v11b.sh: stessi flag, prompt proxy_30, bracci full/dvocab/dvocab_en), binario
# proxy/llama_spec_trace.v14.nollamafile (sorgente proxy/llama_spec_trace_v14.cpp: committed/accepted clampati al primo EOG come v13,
# mtp_process null senza MTP, arbitro solo per --live-src aprime|default_a, qui non usato). Build GGML_LLAMAFILE=OFF (libs build-nollamafile,
# libllama-common gia' con la patch STRATA_DRAFT_VOCAB). Tag nuovi e4v14_*. nice 19, un solo llama alla volta, pre-check CPU, monitor 2 s.
# Regola edit_np (Alessandro 26/10 19:45 CET): prompt proxy_30 divisi in proxy_30_codechat (20) + proxy_30_edit_np (10, concatenazione = proxy_30);
# ogni braccio in due passate, tag e4v14_tf_d7_p30_<n> (code+chat) e e4v14_tf_d7_p30_<n>_edit_np (edit). Modalita' TF: stato per prompt, ordine invariato.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11; B=/workspace/llama.cpp/build-nollamafile; BIN=./proxy/llama_spec_trace.v14.nollamafile
log() { echo "$(date '+%F %T %Z') $*" >> $OUT/campaign.log; }
pre() { log "$1 precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)"; }
[ -x $BIN ] || { log "FAILED e4v14: manca $BIN"; exit 1; }
{ echo "tracer v14 (proxy CPU, non AMD), $(date '+%F %T %Z')"; sha256sum datasets/proxy_30.jsonl datasets/proxy_30_codechat.jsonl datasets/proxy_30_edit_np.jsonl proxy/llama_spec_trace_v14.cpp proxy/strata_arbiter_v1.hpp $BIN $B/bin/libllama-common.so.0.7.0 $B/bin/libllama.so* $B/bin/libggml*.so* 2>/dev/null; ldd $BIN | grep -E 'ggml|llama'; grep GGML_LLAMAFILE $B/CMakeCache.txt; strings $B/bin/libllama-common.so.0.7.0 | grep -c STRATA_DRAFT_VOCAB; } > $OUT/tracer_v14_build_info.txt
log "NOTE tracer version change: E4 usa $BIN (sha256 $(sha256sum $BIN | cut -c1-16), LLAMAFILE OFF); info $OUT/tracer_v14_build_info.txt"
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7 --spec-draft-n-max 7 --mode tf --live-src mtp"
: > $OUT/e4v14_cmds.txt
for v in full: dvocab:/workspace/strata-src/data/draft_vocab.bin dvocab_en:/workspace/strata-src/data/draft_vocab_en.bin; do
 for part in codechat edit_np; do
  n=${v%%:*}; f=${v#*:}; tag=e4v14_tf_d7_p30_$n; PR=datasets/proxy_30_codechat.jsonl
  [ $part = edit_np ] && { tag=${tag}_edit_np; PR=datasets/proxy_30_edit_np.jsonl; }
  [ -f $OUT/$tag.ok ] && { log "$tag gia' completato, salto"; continue; }
  if [ -n "$f" ]; then export STRATA_DRAFT_VOCAB=$f; else unset STRATA_DRAFT_VOCAB; fi
  echo "STRATA_DRAFT_VOCAB=${STRATA_DRAFT_VOCAB:-} nice -n 19 $BIN $FL --prompts $PR --tag $tag --out $OUT/$tag" >> $OUT/e4v14_cmds.txt
  pre $tag
  python3 tools/cpu_foreign.py monitor $OUT/cpu_$tag.log 2 & MON=$!
  log "START $tag"
  nice -n 19 $BIN $FL --prompts $PR --tag $tag --out $OUT/$tag 2> $OUT/$tag.err; e=$?
  kill $MON; wait $MON 2>/dev/null
  log "END $tag exit $e cpu(intervals_ge0.5 max, escl. sand-host): $(python3 tools/cpu_judge.py $OUT/cpu_$tag.log)"
  [ $e -eq 0 ] || { log "FAILED $tag"; exit 1; }; touch $OUT/$tag.ok
 done
done
touch $OUT/e4v14.done; log "e4v14 runs.done"
