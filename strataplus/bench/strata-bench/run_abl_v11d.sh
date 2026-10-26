#!/usr/bin/env bash
# proxy CPU, non AMD. v11d = v11c + pre-check CPU (cpu_foreign wait 30 s <0.5 core) e monitor per ogni run llama; finestre in cpu_busy_bench.log via campaign.log. Unico test di identita' greedy: build -DGGML_LLAMAFILE=OFF (dir separata), verify T=2, ctx 512.
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11
L=/workspace/llama.cpp; B=$L/build-nollamafile
while [ ! -f $OUT/check_v12.done ]; do sleep 15; done
pre() { echo "$(date '+%F %T %Z') $1 precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)" >> $OUT/campaign.log; }
pre build_nollamafile
echo "$(date '+%F %T %Z') START build_nollamafile" >> $OUT/campaign.log
NAT=$(grep -oP 'GGML_NATIVE:BOOL=\K\w+' $L/build/CMakeCache.txt || echo ON)
cmake -S $L -B $B -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_LLAMAFILE=OFF -DLLAMA_CURL=OFF -DGGML_NATIVE=$NAT > logs/nollamafile_cmake.log 2>&1
ninja -C $B -j 6 llama-common > logs/nollamafile_build.log 2>&1
c++ -std=c++17 -O3 -DNDEBUG -DGGML_BACKEND_SHARED -DGGML_SHARED -DGGML_USE_CPU -DLLAMA_SHARED -I$L/common -I$L/vendor -I$L/include -I$L/ggml/include -I/workspace/strata-src/include proxy/llama_spec_trace.cpp build-strata-cpu/libstrata_spec.a -L$B/bin -lllama-common -lllama -lggml -lggml-base -Wl,-rpath,$B/bin -o proxy/llama_spec_trace.v11.nollamafile >> logs/nollamafile_build.log 2>&1
grep -E "LLAMAFILE" $B/CMakeCache.txt >> logs/nollamafile_build.log
echo "$(date '+%F %T %Z') END build_nollamafile" >> $OUT/campaign.log
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 512 -b 512 -ub 512 --no-repack --spec-draft-n-max 3 --prompts datasets/diag_prompts.jsonl"
mkref() { python3 -c "
import json,sys
o=open(sys.argv[2],'w')
for l in open(sys.argv[1]):
    j=json.loads(l)
    if j['type']=='request_end': o.write(j['req_id']+'\t'+','.join(map(str,j['output_ids']))+'\n')" $1 $2; }
for v in llamafile_on:./proxy/llama_spec_trace.v11.bin llamafile_off:./proxy/llama_spec_trace.v11.nollamafile; do
  n=${v%%:*}; BIN=${v#*:}
  echo "$(date '+%F %T %Z') START abl_$n" >> $OUT/campaign.log
  ldd $BIN | grep ggml-cpu > $OUT/abl_${n}.ldd
  pre abl_${n}_base; python3 tools/cpu_foreign.py monitor $OUT/cpu_abl_${n}.log 2 & MON=$!
  $BIN $FL --mode base --dmax 1 --tag abl_${n}_base --out $OUT/abl_${n}_base 2> $OUT/abl_${n}_base.err
  mkref $OUT/abl_${n}_base.jsonl $OUT/abl_${n}_ref.tsv
  pre abl_${n}_ywrong_T2
  $BIN $FL --mode live --live-src ywrong --dmax 1 --ref $OUT/abl_${n}_ref.tsv --tag abl_${n}_ywrong_T2 --out $OUT/abl_${n}_ywrong_T2 2> $OUT/abl_${n}_ywrong_T2.err
  kill $MON; wait $MON 2>/dev/null
  echo "$(date '+%F %T %Z') END abl_$n cpu(intervals_ge0.5 max, escl. sand-host; include i 30 s di precheck): $(python3 tools/cpu_judge.py $OUT/cpu_abl_${n}.log)" >> $OUT/campaign.log
done
touch $OUT/abl.done
