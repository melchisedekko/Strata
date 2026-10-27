#!/usr/bin/env python3
"""proxy CPU, non AMD. Analisi aggiuntiva NON preregistrata: |Δlogit top-1| fra forma (i) e forma (iv) (storia esatta di A1,
round reali con rollback) sui 5 prompt di τ; righe j < committed. Controlla anche (iv) contro i vmargin loggati di A1.
Uso: tauhist_analyze.py PROBE_tau.jsonl PROBE_tauhist.jsonl META_tau.json A1.jsonl OUT.json"""
import json, sys, math
def rows(p):
    R = {}
    for l in open(p):
        x = json.loads(l); R.setdefault(x['job'], []).append(x)
    return R
Ri, Rh, M = rows(sys.argv[1]), rows(sys.argv[2]), json.load(open(sys.argv[3]))
VM = {}
for l in open(sys.argv[4]):
    x = json.loads(l)
    if x['type'] == 'round': VM.setdefault(x['req_id'], []).append(x)
D, G, logdiff, logmis, nlog = [], [], 0.0, 0, 0
for k, m in M.items():
    ri = {x['pos']: x for x in Ri[f'{k}_i']}; H = Rh[f'{k}_iv']; steps = sorted(set(x['step'] for x in H))
    for s, rd in zip(steps, VM[m['req_id']]):
        for x in [y for y in H if y['step'] == s]:
            j = x['row']; vm = rd['vmargin']
            if j < len(vm): nlog += 1; logmis += vm[j][0] != x['top1']; logdiff = max(logdiff, abs(vm[j][2] - x['gap']))
            if j >= rd['committed_raw']: continue
            xi = ri.get(x['pos'])
            if xi is None: continue   # riga che predice oltre l'ultimo token di output (fuori dalla forma (i))
            t = xi['top1']
            v = next((b for a, b in x['top5'] if a == t), None)
            D.append(abs(xi['l1'] - v)); G.append(abs(xi['gap'] - x['gap']))
D.sort(); G.sort(); q = lambda L: L[min(len(L) - 1, math.ceil(0.99 * len(L)) - 1)]
out = {'n_positions': len(D), 'max_dlogit_top1_i_vs_iv': D[-1], 'p99': q(D), 'median': D[len(D) // 2],
       'max_dgap': G[-1], 'p99_dgap': q(G), 'iv_vs_log_rows': nlog, 'iv_vs_log_top1_mismatch': logmis, 'iv_vs_log_max_abs_gap_diff': logdiff}
json.dump(out, open(sys.argv[5], 'w'), indent=1); print(json.dumps(out))
