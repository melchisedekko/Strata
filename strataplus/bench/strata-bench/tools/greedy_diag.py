#!/usr/bin/env python3
"""proxy CPU, non numeri AMD. Diagnosi dell'uguaglianza greedy: per ogni run, prima posizione in cui l'output differisce da base_r0.
Scrive traces/GREEDY_DIAG.md e greedy_diag.json; tools/summarize.py lo inserisce in testa a SUMMARY.md."""
import json, glob, os, collections
RAW = '/workspace/strata-plus/traces/raw'; TR = '/workspace/strata-plus/traces'
def reqs(f):
    d = {}
    for l in open(f):
        try: j = json.loads(l)
        except json.JSONDecodeError: continue
        if j['type'] == 'request': d[j['req_id']] = j
    return d
def rounds(f):
    d = collections.defaultdict(list)
    for l in open(f):
        try: j = json.loads(l)
        except json.JSONDecodeError: continue
        if j['type'] == 'round': d[j['req_id']].append(j)
    return d
def fdiv(o, y):
    d = next((i for i, (a, b) in enumerate(zip(o, y)) if a != b), None)
    if d is None and len(o) != len(y): d = min(len(o), len(y))
    return d
B = reqs(f'{RAW}/base_r0.jsonl')
runs = ['base_r1', 'base_r2', 'tf_d7', 'diag_yright', 'diag_ywrong', 'live_mtp_k1_r0', 'live_mtp_k2_r0', 'live_mtp_k3_r0', 'live_mtp_k3_r1',
        'live_mtp_k3_r2', 'live_mtp_k5_r0', 'live_mtp_k7_r0', 'live_lookup_r0', 'live_lookup_r1', 'live_lookup_r2',
        'live_combo_k3_r0', 'live_combo_k3_r1', 'live_combo_k3_r2']
res = {}
for r in runs:
    p = f'{RAW}/{r}.jsonl'
    if not os.path.exists(p): continue
    R = reqs(p); RD = rounds(p)
    per = {}
    for k, q in R.items():
        d = fdiv(q['output_ids'], B[k]['output_ids'])
        info = {'first_div': d}
        if d is not None:
            # round that produced the divergent token: the one whose committed span covers index d
            for x in RD[k]:
                g = x['gen_index']
                if g <= d < g + len(x['target_tokens']):
                    info.update({'round_T': x['T'], 'offset_in_round': d - g, 'source': x['source'],
                                 'prev_round_rejected': None})
                    break
            prev = [x for x in RD[k] if x['gen_index'] + len(x['target_tokens']) <= d]
            info['rounds_before'] = len(prev)
            info['rounds_before_with_rejection'] = sum(1 for x in prev if x['accepted'] < x['k_proposed'])
            info['rounds_before_T_gt1'] = sum(1 for x in prev if x['T'] > 1)
        per[k] = info
    res[r] = per
json.dump(res, open(f'{TR}/greedy_diag.json', 'w'), indent=1)
ids = [k for k in B if k in res.get('diag_yright', {})]
L = ['## Diagnosi uguaglianza greedy (proxy CPU, non numeri AMD)', '',
     'Riferimento y = base_r0 (decode T=1, nessun draft). Valore = prima posizione dell\'output diversa da y ("=" = identico). '
     '`diag_yright`: ogni round verifica come draft i 7 token corretti di y (T=8, tutti accettati, **nessun rifiuto né rollback**). '
     '`diag_ywrong`: draft = y con ogni id +1 (T=8, sempre rifiutato al 1° token, **rollback a ogni round**, 1 token committato per round).', '']
cols = [r for r in runs if r in res]
L.append('| prompt | dominio | ' + ' | '.join(c.replace('live_', '') for c in cols) + ' |')
L.append('|---|---|' + '---|' * len(cols))
for k in B:
    row = [str(res[c][k]['first_div']) if k in res[c] and res[c][k]['first_div'] is not None else ('=' if k in res[c] else '') for c in cols]
    L.append(f'| {k} | {B[k]["domain"]} | ' + ' | '.join(row) + ' |')
L.append('')
L.append('| run | prompt identici a y | su |')
L.append('|---|---|---|')
for c in cols:
    n = len(res[c]); e = sum(1 for v in res[c].values() if v['first_div'] is None)
    L.append(f'| {c} | {e} | {n} |')
L.append('')
# where in the round does the divergence happen (live runs)
L.append('Posizione del token divergente dentro il round che lo ha prodotto (offset 0 = primo token del round, cioè la predizione dopo id_last):')
L.append('')
L.append('| run | divergenze | round T=1 | round T>1 | di cui offset 0 | round precedenti con rifiuto (mediana) |')
L.append('|---|---|---|---|---|---|')
import statistics as st
for c in cols:
    dv = [v for v in res[c].values() if v['first_div'] is not None and 'round_T' in v]
    if not dv: continue
    L.append(f"| {c} | {len(dv)} | {sum(v['round_T'] == 1 for v in dv)} | {sum(v['round_T'] > 1 for v in dv)} | {sum(v['offset_in_round'] == 0 for v in dv)} | {st.median(v['rounds_before_with_rejection'] for v in dv)} |")
open(f'{TR}/GREEDY_DIAG.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
