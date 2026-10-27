#!/usr/bin/env python3
# diag_greedy_aprime v1 (27/10/2026 CET): aggrega le tracce della diagnosi. proxy CPU, non AMD, llama.cpp non Strata.
# uso: report.py OUT.json SUFFIX   (SUFFIX = '' per codechat, '_<tag edit>' per edit). Sola lettura delle tracce.
import json, sys, math, statistics as st
O = '/workspace/strata-plus/traces/raw/aprime_holdout_v14_ab'; D = 'runs/diag_greedy_aprime_v1'
REF = '/workspace/strata-plus/traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv'
out, sfx = sys.argv[1], sys.argv[2]
def load(p):
    req, rounds = {}, {}
    if p.endswith('.tsv'):
        for l in open(p):
            if '\t' in l: k, v = l.rstrip('\n').split('\t', 1); req[k] = [int(x) for x in v.split(',') if x]
        return req, {}
    for l in open(p):
        d = json.loads(l)
        if d['type'] == 'request': req[d['req_id']] = d['output_ids']
        elif d['type'] == 'round': rounds.setdefault(d['req_id'], []).append(d)
    return req, rounds
def fd(a, b):
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]: return i
    return None if len(a) == len(b) else min(len(a), len(b))
def vm(rounds, d):
    for r in rounds:
        if r['pos'] <= d < r['pos'] + r['committed']:
            i = d - r['pos']; v = r['vmargin'][i]
            return {'T': r['T'], 'row': i, 'top1': v[0], 'top2': v[1], 'gap_logit': round(v[2], 5),
                    'gap_logprob': round(math.log(v[3] / v[4]), 5) if v[3] > 0 and v[4] > 0 else None,
                    'emitted': r['target_tokens'][i], 'emitted_is_top1': r['target_tokens'][i] == v[0]}
    return None
R = {'A1': f'{O}/aprime_r1{sfx}.jsonl', 'B1': f'{O}/default_a_r1{sfx}.jsonl', 'TF3': f'{O}/holdout_tf_cap3_v14{sfx}.jsonl', 'REF': REF}
for t in ['base_r1', 'base_r2', 'aprime_rr1', 'aprime_rr2', 'default_a_rr1', 'default_a_rr2', 'ywrong_d3', 'ywrong_d7', 'yright_d7', 'mtp_cap3']:
    try: open(f'{D}/{t}{sfx}.ok')
    except OSError: continue
    R[t] = f'{D}/{t}{sfx}.jsonl'
L = {k: load(v) for k, v in R.items()}
ids = [json.loads(l)['id'] for l in open(f'{D}/prompts{sfx}.jsonl')]
res = {'label': 'proxy CPU, non AMD, llama.cpp non Strata', 'runs': list(R), 'n_prompts': len(ids), 'compare': {}, 'vm_repro': {}, 'div_logits': []}
def cmp(x, y):
    rows = {q: fd(L[x][0][q], L[y][0][q]) for q in ids if q in L[x][0] and q in L[y][0]}
    return {'n': len(rows), 'identical': sum(v is None for v in rows.values()), 'div': rows}
pairs = [('base_r1', 'base_r2'), ('base_r1', 'TF3'), ('base_r2', 'TF3'), ('base_r1', 'REF'), ('A1', 'B1'), ('A1', 'base_r1'), ('B1', 'base_r1'),
         ('aprime_rr1', 'aprime_rr2'), ('aprime_rr1', 'A1'), ('aprime_rr2', 'A1'), ('default_a_rr1', 'default_a_rr2'), ('default_a_rr1', 'B1'), ('default_a_rr2', 'B1'),
         ('ywrong_d3', 'base_r1'), ('ywrong_d7', 'base_r1'), ('ywrong_d3', 'ywrong_d7'), ('yright_d7', 'base_r1'), ('mtp_cap3', 'base_r1'), ('mtp_cap3', 'A1'), ('mtp_cap3', 'B1')]
for x, y in pairs:
    if x in L and y in L: res['compare'][f'{x}:{y}'] = cmp(x, y)
# riproducibilita' dei logit round per round (vmargin, precisione stampata 5 decimali) fra run ripetute
for x, y in [('aprime_rr1', 'A1'), ('aprime_rr1', 'aprime_rr2'), ('default_a_rr1', 'B1'), ('default_a_rr1', 'default_a_rr2'), ('base_r1', 'base_r2'), ('base_r1', 'TF3')]:
    if x not in L or y not in L: continue
    same = tot = 0
    for q in ids:
        a = L[x][1].get(q, []); b = L[y][1].get(q, [])
        for ra, rb in zip(a, b):
            tot += 1; same += ra['vmargin'] == rb['vmargin'] and ra['proposal'] == rb['proposal'] and ra['target_tokens'] == rb['target_tokens']
        tot += abs(len(a) - len(b))
    res['vm_repro'][f'{x}:{y}'] = {'rounds': tot, 'identical_rounds': same}
# (4) logit alla prima divergenza: batch 1 (base_r1, se condivide il prefisso) vs batch di verifica del round (vmargin della run)
B = 'base_r1' if 'base_r1' in L else 'TF3'
for x, y in [('A1', 'B1'), ('A1', B), ('B1', B)]:
    for q in ids:
        a, b = L[x][0][q], L[y][0][q]; d = fd(a, b)
        if d is None or d >= len(a) or d >= len(b): continue
        e = {'pair': f'{x}:{y}', 'id': q, 'div': d, 'x_tok': a[d], 'y_tok': b[d], 'x_vm': vm(L[x][1][q], d), 'y_vm': vm(L[y][1][q], d)}
        bb = L[B][0][q]
        e['batch1_prefix_ok'] = bb[:d] == a[:d]
        e['batch1_vm'] = vm(L[B][1][q], d) if e['batch1_prefix_ok'] and d < len(bb) else None
        for k in ['x_vm', 'y_vm']:
            if e[k] and e['batch1_vm']: e[k]['argmax_changed_vs_batch1'] = e[k]['top1'] != e['batch1_vm']['top1']
        res['div_logits'].append(e)
gaps = {}
for e in res['div_logits']:
    for k in ['x_vm', 'y_vm', 'batch1_vm']:
        if e[k]: gaps.setdefault(e['pair'], []).append(e[k]['gap_logit'])
def dist(v): return {'n': len(v), 'lt_0.05': sum(g < 0.05 for g in v), '0.05_0.5': sum(0.05 <= g < 0.5 for g in v), 'ge_0.5': sum(g >= 0.5 for g in v),
                     'min': min(v), 'median': st.median(v), 'max': max(v)} if v else None
res['gap_dist'] = {k: dist(v) for k, v in gaps.items()}
res['bug_criterion_violations'] = [e['id'] if not sfx else '-' for e in res['div_logits'] for k in ['x_vm', 'y_vm'] if e[k] and not e[k]['emitted_is_top1'] and e[k]['gap_logit'] >= 0.5]
res['emitted_not_top1'] = sum(1 for e in res['div_logits'] for k in ['x_vm', 'y_vm'] if e[k] and not e[k]['emitted_is_top1'])
json.dump(res, open(out, 'w'), indent=1)
for k, v in res['compare'].items(): print(k, f"{v['identical']}/{v['n']}")
for k, v in res['vm_repro'].items(): print('vm', k, v)
print(json.dumps(res['gap_dist'])); print('emitted_not_top1', res['emitted_not_top1'], 'bug', res['bug_criterion_violations'])
