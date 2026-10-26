#!/usr/bin/env bash
# proxy CPU, non numeri AMD. Campagna tracce strataplus.v1 su llama.cpp CPU (Qwen3.5-2B MTP Q4_K_M).
set -u
cd /workspace/strata-bench
OUT=/workspace/strata-plus/traces/raw
M=models/qwen35-2b-mtp-q4_k_m.gguf
P=datasets/proxy_30.jsonl
COMMON="-m $M --spec-type draft-mtp -t 6 --temp 0 -n 128 -c 4096 -b 4096 -ub 512 --no-repack --prompts $P --dmax 7"
run() { # tag mode src k
  echo "$(date '+%F %T %Z') START $1" >> $OUT/campaign.log
  ./proxy/llama_spec_trace $COMMON --spec-draft-n-max $4 --mode $2 --live-src $3 --tag $1 --out $OUT/$1 2> $OUT/$1.err
  echo "$(date '+%F %T %Z') END $1 exit $?" >> $OUT/campaign.log
}
free -m >> $OUT/campaign.log
# 1) teacher-forced, MTP a Dmax=7 in ogni posizione + lookup (candidati per il replay)
run tf_d7 tf mtp 7
# 2) ABBA a blocchi: B=baseline, A=mtp k3, L=lookup-only, C=combo; ordine diretto/inverso alternato, 3 ripetizioni
for rep in 0 1 2; do
  if [ $((rep % 2)) -eq 0 ]; then ORDER="base mtp3 lookup combo"; else ORDER="combo lookup mtp3 base"; fi
  for c in $ORDER; do
    case $c in
      base)   run base_r$rep base mtp 3 ;;
      mtp3)   run live_mtp_k3_r$rep live mtp 3 ;;
      lookup) run live_lookup_r$rep live lookup 3 ;;
      combo)  run live_combo_k3_r$rep live combo 3 ;;
    esac
  done
done
# 3) gate V1: live MTP a k fisso diverso
for k in 1 2 5 7; do run live_mtp_k${k}_r0 live mtp $k; done
touch $OUT/campaign.done
