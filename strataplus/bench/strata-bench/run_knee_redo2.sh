#!/usr/bin/env bash
# proxy CPU, modello denso, non AMD. Secondo passaggio knee: come run_knee_redo.sh ma criterio CPU che esclude l'infrastruttura sand-host
# (tools/cpu_foreign.py v2 + tools/cpu_judge.py), numerazione tentativi che prosegue, max 4 tentativi in questo passaggio;
# p4_knee_T8.json scritto solo se tutti i blocchi sono presenti (gate in knee_t8.py); knee.done solo se knee_t8.py esce 0.
set -u
cd /workspace/strata-bench
K=/workspace/strata-plus/traces/raw/v11/knee; I=$K/invalid
LOG=/workspace/strata-plus/traces/raw/v11/campaign.log
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
inv() { python3 - "$I/invalid.json" "$1" "$2" <<'P'
import json,sys,os
p,n,r=sys.argv[1:]; d=json.load(open(p)) if os.path.exists(p) else []
d.append({'block':n,'reason':r}); json.dump(d,open(p,'w'),indent=1)
P
}
COMMON="--spec-type draft-mtp --spec-draft-n-max 8 --temp 0 -n 8 -c 4096 -b 4096 --no-repack --prompts datasets/p4_prompts.jsonl --dmax 7 --mode p4 --p4-tlist 1,6,7,8,9,10"
B=(); for c in main_b4 main_b5 llamafile_off_b7 main_b8 ctrl_ub256 ctrl_t8; do B+=("q4km $c"); done
for c in main_b1 llamafile_off_b2 llamafile_off_b3 main_b4 main_b5 llamafile_off_b6 llamafile_off_b7 main_b8 ctrl_ub256 ctrl_t8; do B+=("q8 $c"); done
for e in "${B[@]}"; do set -- $e; mt=$1; c=$2; name=${mt}_$c
  [ -f $K/knee_$name.jsonl ] && continue
  [ $mt = q4km ] && mp=models/qwen35-2b-mtp-q4_k_m.gguf || mp=models/qwen35-2b-mtp-q8_0.gguf
  case $c in main_*) bin=v11knee; reps=25; a="-t 6 -ub 512";; llamafile_off_*) bin=v11knee.nollamafile; reps=25; a="-t 6 -ub 512";;
             ctrl_ub256) bin=v11knee; reps=100; a="-t 6 -ub 256";; ctrl_t8) bin=v11knee; reps=100; a="-t 8 -ub 512";; esac
  n0=$(ls $K/cpu_knee_${name}_a*.log 2>/dev/null | wc -l)
  for k in 1 2 3 4; do att=$((n0 + k))
    w=$(python3 tools/cpu_foreign.py wait 30 0.5 3600); log "knee_$name att $att precheck: $w"
    cmd="./proxy/llama_spec_trace.$bin.bin -m $mp $COMMON --p4-reps $reps $a --tag knee_$name --out $K/knee_$name"
    echo "$cmd" >> $K/cmds.txt
    python3 tools/cpu_foreign.py monitor $K/cpu_knee_${name}_a$att.log 2 & MON=$!
    log "START knee_$name att $att ($a, $reps rep)"
    $cmd 2> $K/knee_$name.err; e=$?
    kill $MON; wait $MON 2>/dev/null
    read nb mx < <(python3 tools/cpu_judge.py $K/cpu_knee_${name}_a$att.log)
    log "END knee_$name att $att exit $e foreign_max_excl_sandhost=$mx intervals_ge0.5=$nb"
    if [ $e -eq 0 ] && [ "$nb" -eq 0 ]; then break; fi
    inv "${name}_a$att" "exit $e; $nb intervalli 2 s con carico estraneo (escl. sand-host) >=0.5 core (max $mx); top: $(awk '$2>=0.5' $K/cpu_knee_${name}_a$att.log | sort -k2 -nr | head -1 | cut -d' ' -f5- | cut -c1-60)"
    mv $K/knee_$name.jsonl $I/knee_${name}_a$att.jsonl; mv $K/knee_$name.err $I/knee_${name}_a$att.err
  done
done
if python3 tools/knee_t8.py >> $LOG 2>&1; then touch /workspace/strata-plus/traces/raw/v11/knee.done; else log "knee_t8.py non ha scritto il JSON (vedi sopra); knee.done NON creato"; fi
