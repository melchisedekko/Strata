#!/usr/bin/env python3
# diag_tiled_mm0 v1 (27/10/2026 CET): prima/dopo GGML_CPU_TILED_MM=0. proxy CPU, non AMD, llama.cpp non Strata. Sola lettura delle tracce.
# uso: diag_tiled_mm0_report.py OUT.json SUFFIX ('' codechat, '_<tag edit>' edit)
import json, sys
O = '/workspace/strata-plus/traces/raw/aprime_holdout_v14_ab'; D = 'runs/diag_greedy_aprime_v1'
out, sfx = sys.argv[1], sys.argv[2]
def load(p):
    req, rounds = {}, {}
    for l in open(p):
        d = json.loads(l)
        if d['type'] == 'request': req[d['req_id']] = d['output_ids']
        elif d['type'] == 'round': rounds.setdefault(d['req_id'], []).append(d)
    return req, rounds
def fd(a, b):
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]: return i
    return None if len(a) == len(b) else min(len(a), len(b))
def T_at(rounds, d):
    for r in rounds:
        if r['pos'] <= d < r['pos'] + max(r['committed'], 1): return r['T']
    return None
R = {'A1': f'{O}/aprime_r1{sfx}.jsonl', 'B1': f'{O}/default_a_r1{sfx}.jsonl'}
for t in ['base_r1', 'base_r2', 'aprime_rr1', 'aprime_rr2', 'default_a_rr1', 'default_a_rr2', 'aprime_tm0', 'default_a_tm0', 'base_tm0']:
    import os
    if os.path.exists(f'{D}/{t}{sfx}.ok') or os.path.exists(f'{D}/{t}{sfx}.ok.orfano'): R[t] = f'{D}/{t}{sfx}.jsonl'
L = {k: load(v) for k, v in R.items()}
ids = [json.loads(l)['id'] for l in open(f'{D}/prompts{sfx}.jsonl')]
div = [q for q in ids if fd(L['A1'][0][q], L['B1'][0][q]) is not None]
G = 'base_r1'
rows = []
for q in div:
    a, b = L['A1'], L['B1']; d = fd(a[0][q], b[0][q])
    r = {'id': q, 'before_A1_B1_pos': d, 'T_A1': T_at(a[1][q], d), 'T_B1': T_at(b[1][q], d),
         'before_A1_G': fd(a[0][q], L[G][0][q]), 'before_B1_G': fd(b[0][q], L[G][0][q])}
    if 'aprime_tm0' in L and 'default_a_tm0' in L:
        x, y = L['aprime_tm0'], L['default_a_tm0']
        r['after_A1_B1'] = fd(x[0][q], y[0][q]); r['after_A1_G'] = fd(x[0][q], L[G][0][q]); r['after_B1_G'] = fd(y[0][q], L[G][0][q])
        dd = r['after_A1_B1']
        if dd is not None: r['after_T_A1'] = T_at(x[1][q], dd); r['after_T_B1'] = T_at(y[1][q], dd)
        if 'base_tm0' in L: r['after_A1_Gtm0'] = fd(x[0][q], L['base_tm0'][0][q]); r['after_B1_Gtm0'] = fd(y[0][q], L['base_tm0'][0][q])
    if 'aprime_tm0' in L and 'default_a_tm0' in L and r['after_A1_B1'] is not None:
        dd = r['after_A1_B1']; r['after_kv'] = [{k: z[k] for k in ('pos', 'T', 'kv_pos', 'ctx_len')} for z in (rr for rr in x[1][q] if rr['pos'] <= dd < rr['pos'] + max(rr['committed'], 1))] + \
            [{k: z[k] for k in ('pos', 'T', 'kv_pos', 'ctx_len')} for z in (rr for rr in y[1][q] if rr['pos'] <= dd < rr['pos'] + max(rr['committed'], 1))]
    r['before_kv'] = [{k: z[k] for k in ('pos', 'T', 'kv_pos', 'ctx_len')} for src in (a, b) for z in src[1][q] if z['pos'] <= d < z['pos'] + max(z['committed'], 1)]
    r['A1_T8_rounds_before_div'] = sum(1 for x in a[1][q] if x['pos'] < d and x['T'] >= 8)
    r['B1_T8_rounds_before_div'] = sum(1 for x in b[1][q] if x['pos'] < d and x['T'] >= 8)
    r['group'] = 'T8' if 8 in (r['T_A1'], r['T_B1']) else 'nonT8'
    rows.append(r)
res = {'label': 'proxy CPU, non AMD, llama.cpp non Strata', 'runs': list(R), 'n_prompts_set': len(ids), 'n_div_A1_B1': len(div), 'rows': rows}
# controlli sull'intero set (inclusi i prompt identici di controllo)
def ident(x, y): return sum(fd(L[x][0][q], L[y][0][q]) is None for q in ids) if x in L and y in L else None
res['set_identical'] = {k: ident(*k.split(':')) for k in ['A1:B1', 'A1:base_r1', 'B1:base_r1', 'aprime_tm0:default_a_tm0', 'aprime_tm0:base_r1', 'default_a_tm0:base_r1',
                        'base_tm0:base_r1', 'aprime_tm0:base_tm0', 'default_a_tm0:base_tm0', 'aprime_tm0:aprime_rr1', 'default_a_tm0:default_a_rr1', 'aprime_rr1:aprime_rr2', 'default_a_rr1:default_a_rr2']}
# effetto della variabile: round con stesso pos fra aprime_rr1 (tiled on) e aprime_tm0, prima della prima divergenza di output, per T
def eff(x, y):
    if x not in L or y not in L: return None
    by = {}
    for q in ids:
        d = fd(L[x][0][q], L[y][0][q]); lim = 10**9 if d is None else d
        for ra, rb in zip(L[x][1].get(q, []), L[y][1].get(q, [])):
            if ra['pos'] != rb['pos'] or ra['pos'] >= lim or ra['T'] != rb['T'] or ra['proposal'] != rb['proposal']: break
            k = 'T>=8' if ra['T'] >= 8 else 'T<8'; s = by.setdefault(k, [0, 0]); s[0] += 1; s[1] += ra['vmargin'] == rb['vmargin']
    return {k: {'rounds_same_input': v[0], 'vmargin_identical': v[1]} for k, v in by.items()}
res['effect_tiled_var'] = {'aprime_rr1:aprime_tm0': eff('aprime_rr1', 'aprime_tm0'), 'aprime_rr1:aprime_rr2': eff('aprime_rr1', 'aprime_rr2'),
                           'default_a_rr1:default_a_tm0': eff('default_a_rr1', 'default_a_tm0')}
# A1 completo (60 code/chat, 30 edit) vs greedy puro batch 1 (TF3), prima (A1 della run v3) e dopo (aprime_tm0_full)
try:
    open(f'{D}/aprime_tm0_full{sfx}.ok'); F = load(f'{D}/aprime_tm0_full{sfx}.jsonl'); A = load(f'{O}/aprime_r1{sfx}.jsonl'); T3 = load(f'{O}/holdout_tf_cap3_v14{sfx}.jsonl')
    ks = sorted(T3[0]); res['full'] = {'n': len(ks), 'before_A1_eq_greedy': sum(fd(A[0][k], T3[0][k]) is None for k in ks),
        'after_A1tm0_eq_greedy': sum(fd(F[0][k], T3[0][k]) is None for k in ks if k in F[0]), 'after_n': sum(k in F[0] for k in ks)}
    if not sfx: res['full']['after_div_ids'] = [k for k in ks if k in F[0] and fd(F[0][k], T3[0][k]) is not None]
except OSError: pass
json.dump(res, open(out, 'w'), indent=1)
