#!/usr/bin/env python3
"""proxy CPU, non AMD. PREREG v2 Parte B: genera lo script di passi per rollback_probe.
Uso: make_rollback_jobs.py DIV_JSON A.jsonl B.jsonl OUT_JOBS
 DIV_JSON = prompt divergenti della v1 (chiavi = req_id). Per ogni prompt e braccio (A1, B1), round testati = accepted < k_proposed con round r+1.
 Varianti: a (storia esatta, S+L a ogni round testato), a2 (ripetizione), per round: c, c2 (da zero), b (senza rollback), d (stessa forma,
 token rifiutati sostituiti con t^1, stesso seq_rm). Q = batch reale del round r+1."""
import json, sys
def load(p):
    req, rnd = {}, {}
    for l in open(p):
        x = json.loads(l)
        if x['type'] == 'request': req[x['req_id']] = x
        elif x['type'] == 'round': rnd.setdefault(x['req_id'], []).append(x)
    return req, rnd
def T(v): return f"{len(v)} " + ' '.join(map(str, v))
ids = list(json.load(open(sys.argv[1])))
arms = {'A1': load(sys.argv[2]), 'B1': load(sys.argv[3])}
J, meta = [], []
for pi, rid in enumerate(ids):
    for arm, (req, rnd) in arms.items():
        inp, out, R = req[rid]['prompt_ids'], req[rid]['output_ids'], rnd[rid]
        assert [x['r'] for x in R] == list(range(len(R)))
        full = inp + out
        def npast(x): return len(inp) - 1 + x['pos']
        def vb(x): return [full[npast(x)]] + x['proposal']
        tested = [i for i, x in enumerate(R) if x['accepted'] < x['k_proposed'] and i + 1 < len(R)]
        g = f"p{pi}{arm}"
        for i in tested:
            x = R[i]; assert len(x['target_tokens']) == x['accepted'] + 1 and x['target_tokens'][:x['accepted']] == x['proposal'][:x['accepted']]
            assert npast(R[i + 1]) == npast(x) + len(x['target_tokens'])
        # (a) e (a2): storia esatta
        for v in ('a', 'a2'):
            J.append(f"J {g}_{v}"); J.append(f"P {T(inp[:-1])}"); ts = set(tested)
            for i, x in enumerate(R):
                if i - 1 in ts: J.append(f"L {g}_{v}_{i-1} {npast(x)} {T(vb(x))}")
                else: J.append(f"B {npast(x)} {T(vb(x))}")
                if i + 1 < len(R):
                    J.append(f"R {npast(x) + len(x['target_tokens'])}")
                    if i in ts: J.append(f"S {g}_{v}_{i}")
            if v == 'a2':
                for i in tested:
                    J += [f"C aa|{g}|{i} {g}_a_{i} {g}_a2_{i}", f"D aa|{g}|{i} {g}_a_{i} {g}_a2_{i}", f"F {g}_a2_{i}"]
        for i in tested:
            x, q = R[i], R[i + 1]; n_new = npast(x) + len(x['target_tokens']); Q = f"{npast(q)} {T(vb(q))}"; a = f"{g}_a_{i}"
            for v in ('c', 'c2'):
                J += [f"J {g}_{v}_{i}", f"P {T(full[:n_new])}", f"S {g}_{v}_{i}", f"L {g}_{v}_{i} {Q}"]
            J += [f"C ac|{g}|{i} {a} {g}_c_{i}", f"D ac|{g}|{i} {a} {g}_c_{i}", f"C cc|{g}|{i} {g}_c_{i} {g}_c2_{i}", f"D cc|{g}|{i} {g}_c_{i} {g}_c2_{i}",
                  f"F {g}_c_{i}", f"F {g}_c2_{i}"]
            for v in ('b', 'd'):
                J += [f"J {g}_{v}_{i}", f"P {T(inp[:-1])}"]
                for y in R[:i]: J += [f"B {npast(y)} {T(vb(y))}", f"R {npast(y) + len(y['target_tokens'])}"]
                acc = x['accepted']; base = [full[npast(x)]] + x['proposal'][:acc]
                if v == 'b': J.append(f"B {npast(x)} {T(base)}")
                else: J += [f"B {npast(x)} {T(base + [t ^ 1 for t in x['proposal'][acc:]])}", f"R {n_new}"]
                J += [f"S {g}_{v}_{i}", f"L {g}_{v}_{i} {Q}", f"C a{v}|{g}|{i} {a} {g}_{v}_{i}", f"D a{v}|{g}|{i} {a} {g}_{v}_{i}", f"F {g}_{v}_{i}"]
            meta.append({'g': g, 'req_id': rid, 'arm': arm, 'r': i, 'T_r': x['T'], 'k_proposed': x['k_proposed'], 'accepted': x['accepted'],
                         'n_new': n_new, 'T_q': q['T'], 'q_vmargin': q['vmargin']})
        J += [f"F {g}_a_{i}" for i in tested]
open(sys.argv[4], 'w').write('\n'.join(J) + '\n')
json.dump(meta, open(sys.argv[4] + '.meta.json', 'w'), indent=1)
print(len([j for j in J if j.startswith('J ')]), 'jobs', len(meta), 'tested rounds', len(J), 'steps')
