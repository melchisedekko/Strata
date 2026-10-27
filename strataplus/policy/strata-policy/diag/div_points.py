#!/usr/bin/env python3
"""proxy CPU, non AMD. arbiter_diag: punti di prima divergenza A1 vs B1 e logit LOGGATI (vmargin) dai round che contengono d.
Uso: div_points.py A.jsonl B.jsonl TF.jsonl OUT.json"""
import json, sys
def load(p):
    req, rnd = {}, {}
    for l in open(p):
        x = json.loads(l)
        if x['type'] == 'request': req[x['req_id']] = x
        elif x['type'] == 'round': rnd.setdefault(x['req_id'], []).append(x)
    return req, rnd
def at(rounds, d):
    for x in rounds:
        if x['pos'] <= d < x['pos'] + x['committed_raw']:
            j = d - x['pos']; v = x['vmargin'][j]
            return {'r': x['r'], 'pos': x['pos'], 'T': x['T'], 'row': j, 'source': x['source'], 'proposal': x['proposal'],
                    'accepted': x['accepted'], 'target_tokens': x['target_tokens'], 'top1': v[0], 'top2': v[1], 'margin': v[2],
                    'draft_tok_at_row': x['proposal'][j] if j < len(x['proposal']) else None}
    return None
A, Ar = load(sys.argv[1]); B, Br = load(sys.argv[2]); T, Tr = load(sys.argv[3])
out = {}
for rid in A:
    a, b = A[rid]['output_ids'], B[rid]['output_ids']
    if a == b: continue
    d = 0
    while d < min(len(a), len(b)) and a[d] == b[d]: d += 1
    t = T[rid]['output_ids']
    out[rid] = {'domain': A[rid]['domain'], 'd': d, 'tokA': a[d] if d < len(a) else None, 'tokB': b[d] if d < len(b) else None,
                'tf_eq_common_prefix': t[:d] == a[:d], 'tokTF': t[d] if d < len(t) else None,
                'A': at(Ar[rid], d), 'B': at(Br[rid], d), 'TF': at(Tr[rid], d) if t[:d] == a[:d] else None,
                'prompt_tokens': A[rid]['prompt_tokens'], 'lenA': len(a), 'lenB': len(b)}
json.dump(out, open(sys.argv[4], 'w'), indent=1)
