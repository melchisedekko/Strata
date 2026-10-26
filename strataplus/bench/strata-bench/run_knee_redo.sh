#!/usr/bin/env bash
# proxy CPU, modello denso, non AMD. Ripresa knee dopo contaminazione (04:43 CET): blocchi contaminati -> knee/invalid/ + invalid.json;
# ogni blocco parte solo quando il carico estraneo (/proc, esclusi llama_spec_trace) e' < 0.5 core per 30 s; monitor a 2 s durante il blocco;
# blocco INVALID se un intervallo ha carico estraneo >= 0.5 core -> spostato in invalid/ e rifatto (max 3 tentativi).
set -u
cd /workspace/strata-bench
K=/workspace/strata-plus/traces/raw/v11/knee; I=$K/invalid; mkdir -p $I
LOG=/workspace/strata-plus/traces/raw/v11/campaign.log
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
inv() { # name reason
  python3 - "$I/invalid.json" "$1" "$2" <<'P'
import json,sys,os
p,n,r=sys.argv[1:]; d=json.load(open(p)) if os.path.exists(p) else []
d.append({'block':n,'reason':r}); json.dump(d,open(p,'w'),indent=1)
P
}
if [ ! -f $I/invalid.json ]; then
  for b in "q4km_main_b4:ps.log 1/23 snapshot con processo estraneo >20% CPU (python3 /tmp/jg/dryrun.py)" \
           "q4km_main_b5:ps.log 10/23 snapshot (python3 holdout_v11.py, /tmp/jg/tune_v11_dry.py)" \
           "q4km_llamafile_off_b7:ps.log 8/24 snapshot (python in /workspace/strata-policy/.venv, suffix_drafter_test_plain)" \
           "q4km_main_b8:ps.log 5/23 snapshot (cc1plus, tests/test_arm_a_default_parity.py)" \
           "q4km_ctrl_ub256:ps.log 15/75 snapshot (clang++-17, apt-get install ROCm, cc1plus)" \
           "q4km_ctrl_t8:ps.log 18/33 snapshot (dpkg-deb, cc1plus, git index-pack); interrotto a meta'"; do
    n=${b%%:*}; inv "$n" "${b#*:}"; mv $K/knee_$n.jsonl $I/knee_$n.jsonl; mv $K/knee_$n.err $I/knee_$n.err
  done
fi
COMMON="--spec-type draft-mtp --spec-draft-n-max 8 --temp 0 -n 8 -c 4096 -b 4096 --no-repack --prompts datasets/p4_prompts.jsonl --dmax 7 --mode p4 --p4-tlist 1,6,7,8,9,10"
B=(); for c in main_b4 main_b5 llamafile_off_b7 main_b8 ctrl_ub256 ctrl_t8; do B+=("q4km $c"); done
for c in main_b1 llamafile_off_b2 llamafile_off_b3 main_b4 main_b5 llamafile_off_b6 llamafile_off_b7 main_b8 ctrl_ub256 ctrl_t8; do B+=("q8 $c"); done
for e in "${B[@]}"; do set -- $e; mt=$1; c=$2; name=${mt}_$c
  [ -f $K/knee_$name.jsonl ] && continue
  [ $mt = q4km ] && mp=models/qwen35-2b-mtp-q4_k_m.gguf || mp=models/qwen35-2b-mtp-q8_0.gguf
  case $c in main_*) bin=v11knee; reps=25; a="-t 6 -ub 512";; llamafile_off_*) bin=v11knee.nollamafile; reps=25; a="-t 6 -ub 512";;
             ctrl_ub256) bin=v11knee; reps=100; a="-t 6 -ub 256";; ctrl_t8) bin=v11knee; reps=100; a="-t 8 -ub 512";; esac
  for att in 1 2 3; do
    w=$(python3 tools/cpu_foreign.py wait 30 0.5 3600); log "knee_$name att $att precheck: $w"
    cmd="./proxy/llama_spec_trace.$bin.bin -m $mp $COMMON --p4-reps $reps $a --tag knee_$name --out $K/knee_$name"
    echo "$cmd" >> $K/cmds.txt
    python3 tools/cpu_foreign.py monitor $K/cpu_knee_${name}_a$att.log 2 & MON=$!
    log "START knee_$name att $att ($a, $reps rep)"
    $cmd 2> $K/knee_$name.err; e=$?
    kill $MON; wait $MON 2>/dev/null
    mx=$(awk 'BEGIN{m=0}{if($2>m)m=$2}END{print m}' $K/cpu_knee_${name}_a$att.log); nb=$(awk '$2>=0.5' $K/cpu_knee_${name}_a$att.log | wc -l)
    log "END knee_$name att $att exit $e foreign_max=$mx intervals_ge0.5=$nb"
    if [ $e -eq 0 ] && [ "$nb" -eq 0 ]; then break; fi
    inv "${name}_a$att" "exit $e; $nb intervalli 2 s con carico estraneo >=0.5 core (max $mx); top: $(sort -k2 -nr $K/cpu_knee_${name}_a$att.log | head -1 | cut -d' ' -f4- | cut -c1-60)"
    mv $K/knee_$name.jsonl $I/knee_${name}_a$att.jsonl; mv $K/knee_$name.err $I/knee_${name}_a$att.err
  done
done
python3 tools/knee_t8.py >> $LOG 2>&1
touch /workspace/strata-plus/traces/raw/v11/knee.done
