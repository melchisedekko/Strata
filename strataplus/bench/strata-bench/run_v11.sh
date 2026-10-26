#!/usr/bin/env bash
# proxy CPU, non AMD. Campagna strataplus.v1.1 (Qwen3.5-2B MTP Q4_K_M, llama.cpp CPU).
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw/v11
mkdir -p $OUT
BIN=./proxy/llama_spec_trace.v11.bin
M=models/qwen35-2b-mtp-q4_k_m.gguf
FL="-m $M --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7"
P30=datasets/proxy_30.jsonl; AG=datasets/agent_turns_bench.jsonl; MT=datasets/mtbench2.jsonl; DG=datasets/diag_prompts.jsonl
log() { echo "$(date '+%F %T %Z') $*" >> $OUT/campaign.log; }
run() { # tag prompts mode src k [extra...]
  local tag=$1 p=$2 mode=$3 src=$4 k=$5; shift 5
  log "START $tag ps_heavy=$(ps -eo comm,args | grep -E 'run_v2|llama|python3 .*sim' | grep -v grep | grep -vc llama_spec_trace)"
  $BIN $FL --spec-draft-n-max $k --prompts $p --mode $mode --live-src $src --tag $tag --out $OUT/$tag "$@" 2> $OUT/$tag.err
  log "END $tag exit $?"
}
mkref() { python3 - "$@" <<'P'
import json,sys
out=open(sys.argv[-1],'w')
for f in sys.argv[1:-1]:
    for l in open(f):
        j=json.loads(l)
        if j.get('type')=='request_end': out.write(j['req_id']+'\t'+','.join(map(str,j['output_ids']))+'\n')
P
}
free -m >> $OUT/campaign.log
run base_p30 $P30 base mtp 3
run agent_turns_bench_base $AG base mtp 3
run mtbench2_base $MT base mtp 3
mkref $OUT/base_p30.jsonl $OUT/agent_turns_bench_base.jsonl $OUT/mtbench2_base.jsonl $OUT/ref_base.tsv
R="--ref $OUT/ref_base.tsv"
run live_mtp_k3_p30 $P30 live mtp 3 $R
run agent_turns_bench_live_mtp_k3 $AG live mtp 3 $R
run mtbench2_live_mtp_k3 $MT live mtp 3 $R
run tf_d7_p30 $P30 tf mtp 7
run agent_turns_bench_tf_d7 $AG tf mtp 7 $R
run mtbench2_tf_d7 $MT tf mtp 7 $R
run live_lookup_p30 $P30 live lookup 3 $R
run agent_turns_bench_live_lookup $AG live lookup 3 $R
run live_combo_p30 $P30 live combo 3 $R
run agent_turns_bench_live_combo $AG live combo 3 $R
for d in 1 3 7; do
  run diag_yright_T$((d+1)) $DG live yright 3 $R --dmax $d
  run diag_ywrong_T$((d+1)) $DG live ywrong 3 $R --dmax $d
done
touch $OUT/campaign.done
