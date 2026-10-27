#!/usr/bin/env python3
"""proxy CPU, non AMD. Validazione di logit_probe: forma (i) contro i vmargin loggati dalla run TF (holdout_tf_cap3_v14), riga 0 di ogni round.
Uso: check_probe_vs_tf.py TF.jsonl PROBE.jsonl META.json SUFFIX"""
import json, sys
TF = {}
for l in open(sys.argv[1]):
    x = json.loads(l)
    if x['type'] == 'request': TF.setdefault(x['req_id'], {})['plen'] = len(x['prompt_ids'])
    if x['type'] == 'round': TF.setdefault(x['req_id'], {})[x['pos']] = x['vmargin'][0]
R = {}
for l in open(sys.argv[2]):
    try: x = json.loads(l)
    except Exception: continue
    R.setdefault(x['job'], []).append(x)
M = json.load(open(sys.argv[3])); tot = [0, 0, 0.0]
for k, m in M.items():
    t = TF[m['req_id']]; n = mis = 0; w = 0.0
    for x in R.get(k + sys.argv[4], []):
        p = x['pos'] - (t['plen'] - 1)
        if p in t: n += 1; mis += (t[p][0] != x['top1']); w = max(w, abs(t[p][2] - x['gap']))
    tot[0] += n; tot[1] += mis; tot[2] = max(tot[2], w)
    print(k, 'rows', n, 'top1_mismatch', mis, 'max_abs_gap_diff', w)
print('TOTAL rows', tot[0], 'top1_mismatch', tot[1], 'max_abs_gap_diff', tot[2])
