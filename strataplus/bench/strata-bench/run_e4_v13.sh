#!/usr/bin/env bash
# proxy CPU, non AMD. E4 con tracer v13 (= run_e4_v11b.sh, stessi flag/prompt/bracci, ma binario proxy/llama_spec_trace.v13.bin:
# committed/accepted limitati al primo EOG, errata holdout_lookup_v12, steering 25/10 08:00 CET). Build contro build/ (GGML_LLAMAFILE=ON)
# come llama_spec_trace.v11.bin, dopo il rebuild di llama-common con la patch STRATA_DRAFT_VOCAB. Tag nuovi e4v13_*.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11; B=/workspace/llama.cpp/build; L=/workspace/llama.cpp; BIN=./proxy/llama_spec_trace.v13.bin
pre() { echo "$(date "+%F %T %Z") $1 precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)" >> $OUT/campaign.log; }
pre rebuild_llama_common_e4
echo "$(date '+%F %T %Z') START rebuild_llama_common_e4" >> $OUT/campaign.log
nice -n 19 ninja -C $B -j 6 llama-common > logs/llama_common_rebuild_e4.log 2>&1
echo "$(date '+%F %T %Z') END rebuild_llama_common_e4 exit $?" >> $OUT/campaign.log
pre build_tracer_v13
echo "$(date '+%F %T %Z') START build_tracer_v13" >> $OUT/campaign.log
nice -n 19 c++ -std=c++17 -O3 -DNDEBUG -DGGML_BACKEND_SHARED -DGGML_SHARED -DGGML_USE_CPU -DLLAMA_SHARED -I$L/common -I$L/vendor -I$L/include -I$L/ggml/include -I/workspace/strata-src/include proxy/llama_spec_trace_v13.cpp build-strata-cpu/libstrata_spec.a -L$B/bin -lllama-common -lllama -lggml -lggml-base -Wl,-rpath,$B/bin -o $BIN > logs/build_tracer_v13.log 2>&1; e=$?
echo "$(date '+%F %T %Z') END build_tracer_v13 exit $e" >> $OUT/campaign.log
[ $e -eq 0 ] || exit 1
{ echo "tracer v13 (proxy CPU, non AMD), $(date '+%F %T %Z')"; sha256sum proxy/llama_spec_trace_v13.cpp $BIN $B/bin/libllama-common.so* $B/bin/libllama.so* 2>/dev/null; } > $OUT/tracer_v13_build_info.txt
echo "$(date '+%F %T %Z') NOTE tracer version change: E4 e successivi usano $BIN (sorgente proxy/llama_spec_trace_v13.cpp), committed limitato al primo EOG; info $OUT/tracer_v13_build_info.txt" >> $OUT/campaign.log
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7 --spec-draft-n-max 7 --prompts datasets/proxy_30.jsonl --mode tf --live-src mtp"
for v in full: dvocab:/workspace/strata-src/data/draft_vocab.bin dvocab_en:/workspace/strata-src/data/draft_vocab_en.bin; do
  n=${v%%:*}; f=${v#*:}
  pre e4v13_tf_d7_p30_$n
  echo "$(date '+%F %T %Z') START e4v13_tf_d7_p30_$n" >> $OUT/campaign.log
  if [ -n "$f" ]; then export STRATA_DRAFT_VOCAB=$f; else unset STRATA_DRAFT_VOCAB; fi
  python3 tools/cpu_foreign.py monitor $OUT/cpu_e4v13_$n.log 2 & MON=$!
  nice -n 19 $BIN $FL --tag e4v13_tf_d7_p30_$n --out $OUT/e4v13_tf_d7_p30_$n 2> $OUT/e4v13_tf_d7_p30_$n.err; e=$?
  kill $MON; wait $MON 2>/dev/null
  echo "$(date '+%F %T %Z') END e4v13_tf_d7_p30_$n exit $e cpu: $(python3 tools/cpu_judge.py $OUT/cpu_e4v13_$n.log)" >> $OUT/campaign.log
done
touch $OUT/e4v13.done
