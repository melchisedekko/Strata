#!/usr/bin/env bash
# proxy CPU, non AMD, llama.cpp non Strata. Tracce H-LANG/edit-fix (HumanEvalFix, 5 linguaggi JS/Java/Go/CPP/Rust): tune 40 N (200 item,
# 5 fold) e holdout 40 N (200 item); le 84 N di riserva NON si tracciano. Spec: runs/hlang_editfix_traces_v1.md (leggere prima).
# SCRITTO, NON LANCIATO (27/10/2026 CET): si lancia solo su richiesta esplicita, in una finestra annunciata, DOPO le 10 build ROCm 6.4.4 e la (a')
# (AMD_PROTOCOL_v5.md sez. 14), mai in sovrapposizione con build o altre run.
# Split: run file di Policy run_hlang_editfix.json. Riferimento di pre-registrazione sha256 bbb9eb22… (lic_rm/orig_2026-10-27/workspace/strata-policy/
# replay/), copia pubblica per il fork sha256 dd1b8ee8… (strata-policy/replay/); differiscono SOLO alla riga 291 (nota di pubblicazione): split, seed,
# soglie identici. Lo script verifica lo sha di ogni copia presente, usa lo split del riferimento se c'e' (altrimenti della copia pubblica) e,
# se ci sono entrambe, si ferma se gli split differiscono.
# Tracer e formato = tune H-CA (run_v11.sh, run tf_d7_p30): proxy/llama_spec_trace.v11.bin, teacher-forced, --dmax 7 --spec-draft-n-max 7 (cap 8),
# greedy (--temp 0), stessi flag; domain = category = 'edit-fix' (mai sommato a edit). Post: tools/annotate_v11.py (schema strataplus.v1.1).
# Regole: nice 19, UN solo processo llama alla volta (controllo prima di ogni passata), CPU libera (cpu_foreign wait) prima di ogni passata,
# monitor CPU 2 s, START/END in campaign.log e in /workspace/strata-bench/cpu_busy_bench.log (via tools/bench_window_log.py se vivo,
# altrimenti scritti qui), comandi/hardware/versioni registrati.
set -u
cd /workspace/strata-bench
RAW=/workspace/strata-plus/traces/raw/hlang_editfix_v1; ANN=/workspace/strata-plus/traces/hlang_editfix_v1
LOG=/workspace/strata-plus/traces/raw/v11/campaign.log; BUSY=/workspace/strata-bench/cpu_busy_bench.log
BIN=./proxy/llama_spec_trace.v11.bin; B=/workspace/llama.cpp/build
PT=datasets/hlang_editfix_tune.jsonl; PH=datasets/hlang_editfix_holdout.jsonl; PM=datasets/hlang_editfix_prompts_meta.json
SREF=/workspace/lic_rm/orig_2026-10-27/workspace/strata-policy/replay/run_hlang_editfix.json; SREF_SHA=bbb9eb220f5a6aa5e95f15f05b85d9daf2e1684e7da86506a17cca4b8f103dde
SPUB=/workspace/strata-policy/replay/run_hlang_editfix.json; SPUB_SHA=dd1b8ee8a9932331d15244e220791f975c5800fe224d16778ab70d8a85661d0e
PYA=${PYA:-/tmp/venv_pa/bin/python}   # python con pyarrow (solo per la verifica di split/prompt, nessun modello)
log() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
mkdir -p $RAW/tune $RAW/holdout
MIRROR=1; pgrep -f 'tools/bench_window_log.py' >/dev/null || MIRROR=0
win_start() { log "START $1"; [ $MIRROR = 1 ] || echo "$(date '+%F %T') | (in corso) | START $1  (strata-bench, scritto da run hlang_editfix v1) |" >> $BUSY; WS=$(date '+%F %T'); }
win_end() { log "END $1 $2"; [ $MIRROR = 1 ] || echo "$WS | $(date '+%F %T') | $1  (strata-bench, 1 processo llama, scritto da run hlang_editfix v1) | $2" >> $BUSY; }
# 1) split di Policy: sha di ogni copia presente
NS=0
if [ -f $SREF ]; then echo "$SREF_SHA  $SREF" | sha256sum -c --quiet || { log "FAILED hlang_editfix_v1: sha256 del riferimento run_hlang_editfix.json diverso"; exit 1; }; NS=$((NS+1)); fi
if [ -f $SPUB ]; then echo "$SPUB_SHA  $SPUB" | sha256sum -c --quiet || { log "FAILED hlang_editfix_v1: sha256 della copia pubblica run_hlang_editfix.json diverso"; exit 1; }; NS=$((NS+1)); fi
[ $NS -ge 1 ] || { log "FAILED hlang_editfix_v1: nessuna copia di run_hlang_editfix.json"; exit 1; }
# 2) input fissati (se uno non coincide: stop)
sha256sum -c --quiet <<SHA || { log "FAILED hlang_editfix_v1: sha256 degli input diverso dal run file"; exit 1; }
f3f3ef188648ca9eb4d2d1a5331deba766203a438f70fe01b5d9f45bc5c037df  $BIN
9823702776ab1afe487355cd7a76bacf94fce84db9ec7ad9ec6a637250dde786  $B/bin/libllama-common.so.0.7.0
e373ccc6332269d7216f063443bdc712f3d80fa539104b4b0b6bebd26c7e2316  $B/bin/libllama.so.0.7.0
75b39048253d77f3c99948adf82c187f3fd050069fb9a4bbe36c20fe2e944d51  $B/bin/libggml-base.so.0.27.0
e7879a7d673739d005fae796aa61ecc5a830acd2c9306a2df140fd768c0e04ca  $B/bin/libggml-cpu.so.0.27.0
a5db187c84770dc7f00013016df7cd179194b310089d718168e7def584b8c8e3  $B/bin/libggml.so.0.27.0
18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b  models/qwen35-2b-mtp-q4_k_m.gguf
101bfa2ea7c1d06fa95fd792735f87a4fcb54710e32d3931b594a799df6947f2  $PT
b207b9edd407d47cbfcf8c1d65a2db4910bd0622fa552cf1c75d6cb8650c264e  $PH
31414e21efeef4fd9b922965643e66ea88105db00cb71c4540e435128553634a  $PM
f62a22b6f9c96750eef8ca96fb98266985c1d0847ec81abdd76385ffe811f135  tools/prepare_hlang_editfix_prompts.py
344a793b42fb7cfc100698177a3b5207e6686dba591064f205d2c13471da49a3  LANG_LABEL_RULE.md
5940751543c5a6f4d1ec7e6a12f6173b1f5491a79578326f9a6d195588081df8  tools/annotate_v11.py
f4276c7bcb733f7013f8b52854e010c7a456e9f029c6a950cb36eedd53fb2263  tools/cpu_foreign.py
8fb3e560689cd6784235feb2e899f63fec164a7324a2cee1e5a196459c6c027f  tools/cpu_judge.py
SHA
# 3) split identico tra le copie presenti + prompt rigenerati dallo split (sha dei 5 parquet verificati dentro) identici ai file: altrimenti stop
nice -n 19 $PYA tools/prepare_hlang_editfix_prompts.py datasets --check > $RAW/split_check.json 2> $RAW/split_check.err \
  || { log "FAILED hlang_editfix_v1: verifica split/prompt fallita ($(tail -1 $RAW/split_check.err))"; exit 1; }
python3 -c "import json,sys; a,b=(json.load(open(x)) for x in sys.argv[1:]); k=lambda m:{x:y for x,y in m.items() if x not in ('split_source','split_source_sha256','copies_found_sha256')}; sys.exit(0 if k(a)==k(b) else 1)" $RAW/split_check.json $PM \
  || { log "FAILED hlang_editfix_v1: split/metadati diversi da $PM"; exit 1; }   # la fonte (riferimento o copia pubblica) puo' variare, il resto no
log "hlang_editfix_v1: split verificato (copie presenti: $NS; $(python3 -c "import json;m=json.load(open('$PM'));print('fonte',m['split_source_sha256'][:8],'L1/L2',m['lang_label_L1_L2_agreement'])"))"
nollama() { pgrep -f 'llama_spec_trace|llama-cli|llama-server|llama-bench|llama-' >/dev/null && { log "FAILED hlang_editfix_v1: un altro processo llama e' attivo"; exit 1; }; return 0; }
nollama
unset STRATA_DRAFT_VOCAB
# 4) registrazione: comandi, hardware, versioni (prima di ogni llama)
{ echo "# proxy CPU, non AMD, llama.cpp non Strata"; date '+%F %T %Z'; uname -a; lscpu; nproc; free -m; cat /proc/loadavg
  gcc --version | head -1; cmake --version 2>/dev/null | head -1; python3 --version; $PYA --version; $PYA -c 'import pyarrow; print("pyarrow", pyarrow.__version__)'
  echo "llama.cpp $(git -C /workspace/llama.cpp rev-parse HEAD 2>&1) dirty_files=$(git -C /workspace/llama.cpp status --short 2>/dev/null | wc -l)"
  grep -E 'GGML_LLAMAFILE|GGML_NATIVE|CMAKE_BUILD_TYPE:' $B/CMakeCache.txt 2>/dev/null
  env | grep -E '^(STRATA|GGML|LLAMA|OMP)' | sort
  sha256sum $BIN proxy/llama_spec_trace.cpp $B/bin/lib*.so* models/qwen35-2b-mtp-q4_k_m.gguf $PT $PH $PM $SREF $SPUB tools/prepare_hlang_editfix_prompts.py tools/annotate_v11.py tools/cpu_foreign.py tools/cpu_judge.py LANG_LABEL_RULE.md run_v11.sh runs/run_hlang_editfix_traces_v1.sh 2>&1
  sha256sum datasets/humanevalfix_9a41762f/*/*.parquet
  ldd $BIN | grep -E 'ggml|llama'; } > $RAW/build_env_info.txt 2>&1
# flag = run_v11.sh (FL + run tf_d7_p30 ... tf mtp 7)
FL="-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7 --spec-draft-n-max 7 --mode tf --live-src mtp"
touch $RAW/cmds.txt
# una passata: $1 = split (tune|holdout), $2 = prompt; tag NON inizia con "holdout" (annotate_v11 rinominerebbe per dominio)
pass() {
  D=$RAW/$1; tag=editfix_${1}_tf_d7
  [ -f $D/$tag.ok ] && { log "$tag gia' completato, salto"; return 0; }
  nollama
  echo "nice -n 19 $BIN $FL --prompts $2 --tag $tag --out $D/$tag" >> $RAW/cmds.txt
  log "$tag precheck: $(python3 tools/cpu_foreign.py wait 30 0.5 3600)"
  python3 tools/cpu_foreign.py monitor $D/cpu_$tag.log 2 & MON=$!
  win_start $tag
  nice -n 19 $BIN $FL --prompts $2 --tag $tag --out $D/$tag 2> $D/$tag.err; e=$?
  kill $MON; wait $MON 2>/dev/null
  win_end $tag "exit $e cpu(intervals_ge0.5 max, escl. sand-host): $(python3 tools/cpu_judge.py $D/cpu_$tag.log)"
  [ $e -eq 0 ] || { log "FAILED $tag"; exit 1; }
  grep -q '^skip ' $D/$tag.err && { log "FAILED $tag: prompt saltati dal tracer ($(grep -c '^skip ' $D/$tag.err))"; exit 1; }
  touch $D/$tag.ok
}
pass tune $PT
pass holdout $PH
# 5) post (nessun llama): annotate per split, ref = output proprio del tf (verify T=1 = greedy T=1), come run_check_v12.sh
for s in tune holdout; do
  rm -rf $ANN/$s
  (cd tools && ANN_RAW=$RAW/$s ANN_OUT=$ANN/$s ANN_SPLIT=editfix_$s ANN_REF_GLOB="editfix_${s}_tf_d7.jsonl" nice -n 19 python3 annotate_v11.py > $RAW/annotate_$s.log 2>&1) \
    || { log "FAILED hlang_editfix_v1 annotate $s"; exit 1; }
  rm -f $ANN/$s/holdout_counts.json
  # controllo: 200 richieste, domain 'edit-fix', 40 per linguaggio, ids = prompt file, greedy_equal_ref su tutte
  nice -n 19 python3 - $ANN/$s/editfix_${s}_tf_d7.jsonl datasets/hlang_editfix_$s.jsonl > $RAW/validate_$s.out 2>&1 <<'P' || { log "FAILED hlang_editfix_v1 validate $s: $(tail -1 $RAW/validate_$s.out)"; exit 1; }
import collections, json, sys
want = [json.loads(l) for l in open(sys.argv[2])]; rq = [j for j in map(json.loads, open(sys.argv[1])) if j.get('type') == 'request']
ids = [r['req_id'] for r in rq]; assert sorted(ids) == sorted(w['id'] for w in want), 'ids diversi dal prompt file'
assert len(rq) == 200 and {r['domain'] for r in rq} == {'edit-fix'}, 'conteggio o domain errato'
assert all(r['greedy_equal_ref'] for r in rq), 'greedy_equal_ref falso'
c = collections.Counter(i.split('/')[0] for i in ids); assert set(c.values()) == {40} and len(c) == 5, c
print('ok', len(rq), dict(c))
P
  cp $RAW/cmds.txt $RAW/build_env_info.txt $ANN/$s/
  (cd $ANN/$s && for f in $(ls | grep -v MANIFEST.sha256); do sha256sum $f; done > MANIFEST.sha256 && sha256sum -c --quiet MANIFEST.sha256) || { log "FAILED hlang_editfix_v1 manifest $s"; exit 1; }
done
(cd $RAW && sha256sum cmds.txt build_env_info.txt split_check.json */*.jsonl */*.err */cpu_*.log validate_*.out annotate_*.log > MANIFEST.sha256)
touch $RAW/hlang_editfix_v1.done; log "hlang_editfix_v1 done (MANIFEST raw $(sha256sum $RAW/MANIFEST.sha256 | cut -c1-16))"
