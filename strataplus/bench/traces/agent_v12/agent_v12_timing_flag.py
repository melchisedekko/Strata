#!/usr/bin/env python3
"""proxy CPU, non AMD. agent_v12 (Lead 08:24 CET): tutti i campi di tempo dell'intera serie marcati 'non usabili come misura'.
Metriche riportate: solo AL, greedy_equal_ref, first_divergence_pos (conteggi deterministici)."""
import json, sys, glob
V = sys.argv[1]
NOTE = ("non usabili come misura (intera serie agent_v12): carico CPU estraneo durante i run, intervalli >=0.5 core nei cpu_agent_v12_*.log "
        "(tra cui Policy: breakeven_dsecond.py ~08:07:53-55, download non annunciato wheel cccl/curand 08:18:55-08:19:13 e check di sintassi "
        "CUDA/HIP P-T12 ~08:10-08:24 CET; finestre esatte in cpu_busy_policy.log, copia snapshot in questa cartella)")
TK = ('ms_measured', 'prefill_ms', 'decode_ms', 'draft_ms', 'verify_ms', 'mtp_process_ms', 'ms', 'round_ms', 'tok_s')
REP = ['AL (full, pre_div; committed limitato all EOS)', 'greedy_equal_ref', 'first_divergence_pos']
n = 0
for f in sorted(glob.glob(f'{V}/agent_v12_*.jsonl')):
    rows = [json.loads(l) for l in open(f)]
    for j in rows:
        if j['type'] == 'header': j['timing_validity'] = NOTE; j['metrics_reported'] = REP
        elif j['type'] in ('request', 'request_end'):
            ks = [k for k in j if k in TK or k.endswith('_ms')]
            if ks: j['timing_validity'] = 'non usabili come misura'; j['timing_fields_flagged'] = ks; n += 1
    open(f, 'w').write('\n'.join(json.dumps(j, ensure_ascii=False) for j in rows) + '\n')
print(json.dumps({'requests_flagged': n, 'note': NOTE}, ensure_ascii=False))
