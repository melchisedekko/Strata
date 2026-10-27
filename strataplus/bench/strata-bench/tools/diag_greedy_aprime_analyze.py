#!/usr/bin/env python3
# diag_greedy_aprime v1 (27/10/2026 CET). proxy CPU, non AMD, llama.cpp non Strata. Sola lettura delle tracce.
# Per ogni coppia di run (X,Y): prima divergenza d degli output_ids; logit del target al prefisso comune letti da vmargin
# (riga del round che copre d in ciascuna run: top1, top2, gap logit, p1, p2, T del round) -> gap batch-T del round.
# uso: analyze.py OUT.json name=path.jsonl [name=path.jsonl ...]   (opz. --pairs a:b,c:d)
import json, sys, math
def load(p):
    req, rounds = {}, {}
    if p.endswith('.tsv'):   # riferimento greedy salvato: id \t token,token,...
        for l in open(p):
            if '\t' in l:
                k, v = l.rstrip('\n').split('\t', 1); req[k] = {'output_ids': [int(x) for x in v.split(',') if x]}; rounds[k] = []
        return req, rounds
    for l in open(p):
        d = json.loads(l)
        if d['type'] == 'request': req[d['req_id']] = d
        elif d['type'] == 'round': rounds.setdefault(d['req_id'], []).append(d)
    return req, rounds
def firstdiv(a, b):
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]: return i
    return None if len(a) == len(b) else min(len(a), len(b))
def vm_at(rounds, d):
    for r in rounds:
        if r['pos'] <= d < r['pos'] + r['committed']:
            i = d - r['pos']; v = r['vmargin'][i]
            return {'round': r['r'], 'T': r['T'], 'row': i, 'source': r['source'], 'top1': v[0], 'top2': v[1], 'gap_logit': v[2],
                    'p1': v[3], 'p2': v[4], 'gap_logprob': (math.log(v[3]) - math.log(v[4])) if v[3] > 0 and v[4] > 0 else None,
                    'emitted': r['target_tokens'][i], 'emitted_is_top1': r['target_tokens'][i] == v[0]}
    return None
def main():
    out = sys.argv[1]; runs = {}; pairs = None
    for a in sys.argv[2:]:
        if a.startswith('--pairs='): pairs = [tuple(x.split(':')) for x in a[8:].split(',')]
        else: k, p = a.split('=', 1); runs[k] = load(p)
    names = list(runs)
    if pairs is None: pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
    res = {'label': 'proxy CPU, non AMD, llama.cpp non Strata', 'pairs': {}}
    for x, y in pairs:
        if y == 'REFTOK':   # riferimento salvato (ref_tokens della run x)
            ids = sorted(runs[x][0]); rows = []
            for q in ids:
                a = runs[x][0][q]['output_ids']; b = runs[x][0][q]['ref_tokens']
                d = firstdiv(a, b); rows.append({'id': q, 'div': d, 'x_tok': a[d] if d is not None and d < len(a) else None,
                                                 'y_tok': b[d] if d is not None and d < len(b) else None,
                                                 'x_vm': vm_at(runs[x][1][q], d) if d is not None and d < len(a) else None})
        else:
            ids = sorted(set(runs[x][0]) & set(runs[y][0])); rows = []
            for q in ids:
                a = runs[x][0][q]['output_ids']; b = runs[y][0][q]['output_ids']
                d = firstdiv(a, b)
                rows.append({'id': q, 'div': d, 'x_tok': a[d] if d is not None and d < len(a) else None, 'y_tok': b[d] if d is not None and d < len(b) else None,
                             'x_vm': vm_at(runs[x][1][q], d) if d is not None and d < len(a) else None,
                             'y_vm': vm_at(runs[y][1][q], d) if d is not None and d < len(b) else None})
        res['pairs'][f'{x}:{y}'] = {'n': len(rows), 'identical': sum(r['div'] is None for r in rows), 'rows': rows}
    json.dump(res, open(out, 'w'), indent=1)
    for k, v in res['pairs'].items(): print(k, v['identical'], '/', v['n'])
main()
