#!/usr/bin/env python3
"""proxy CPU, non AMD. arbiter_diag: genera gli script di passi per logit_probe (forme (i)-(v)) dalle tracce A1/B1.
Uso: make_jobs.py tau  A.jsonl B.jsonl OUT_JOBS N_PROMPTS MIN_OUT        (soglia τ: prompt NON divergenti, forme (i) e (ii))
     make_jobs.py tauhist A.jsonl B.jsonl OUT_JOBS N MIN_OUT   (aggiunta NON preregistrata: forma (iv) storia esatta di A1 sugli stessi 5 prompt)
     make_jobs.py div  A.jsonl B.jsonl OUT_JOBS                          (prompt divergenti: forme (i),(ii),(iii),(iv),(v))
Forme (posizione d = indice del token di output; plen = token del prompt; contesto comune out[:d]):
 (i)   P(inp[:-1]) poi un token per batch: inp[-1], out[0..d-1] (prefill + decodifica a batch 1, come TF/base)
 (ii)  P((inp+out)[:plen-1+p]) poi B(plen-1+p, [id_last]+proposal) del round di A1 che ha committato d (p = pos del round)
 (iii) idem con il round di B1
 (iv)  storia esatta di A1: P(inp[:-1]) poi tutti i round di A1 fino a quello che contiene d (B + seq_rm come il tracer L396-480)
 (v)   idem con B1"""
import json, sys
def load(p):
    req, rnd, order = {}, {}, []
    for l in open(p):
        x = json.loads(l)
        if x['type'] == 'request': req[x['req_id']] = x; order.append(x['req_id'])
        elif x['type'] == 'round': rnd.setdefault(x['req_id'], []).append(x)
    return req, rnd, order
def toks(v): return f"{len(v)} " + ' '.join(map(str, v))
def form_i(J, name, inp, out, d, rec_all):
    J.append(f"J {name}"); J.append(f"P {toks(inp[:-1])}")
    seq = [inp[-1]] + out[:d]
    for k, t in enumerate(seq):
        J.append(f"B {len(inp) - 1 + k} {1 if (rec_all or k == d) else 0} {toks([t])}")
def form_round(J, name, inp, out, x):
    p = x['pos']; ctx = (inp + out)[:len(inp) - 1 + p]; idl = (inp + out)[len(inp) - 1 + p]
    J.append(f"J {name}"); J.append(f"P {toks(ctx)}"); J.append(f"B {len(inp) - 1 + p} 1 {toks([idl] + x['proposal'])}")
def form_hist(J, name, inp, out_own, rounds, upto_r):
    J.append(f"J {name}"); J.append(f"P {toks(inp[:-1])}")
    for x in rounds:
        p = x['pos']; n_past = len(inp) - 1 + p; idl = (inp + out_own)[n_past]
        J.append(f"B {n_past} 1 {toks([idl] + x['proposal'])}")
        if x['r'] == upto_r: break
        J.append(f"R {n_past + len(x['target_tokens'])}")
def covering(rounds, d):
    for x in rounds:
        if x['pos'] <= d < x['pos'] + x['committed_raw']: return x
mode = sys.argv[1]
A, Ar, order = load(sys.argv[2]); B, Br, _ = load(sys.argv[3]); J = []
meta = {}
if mode in ('tau', 'tauhist'):
    n, mn = int(sys.argv[5]), int(sys.argv[6]); chosen = []
    for rid in order:
        if A[rid]['output_ids'] == B[rid]['output_ids'] and len(A[rid]['output_ids']) >= mn: chosen.append(rid)
        if len(chosen) == n: break
    for i, rid in enumerate(chosen):
        inp, out = A[rid]['prompt_ids'], A[rid]['output_ids']
        if mode == 'tauhist':
            form_hist(J, f"tau{i}_iv", inp, out, Ar[rid], Ar[rid][-1]['r']); continue
        form_i(J, f"tau{i}_i", inp, out, len(out) - 1, True)
        for x in Ar[rid]: form_round(J, f"tau{i}_ii_r{x['r']}", inp, out, x)
        meta[f"tau{i}"] = {'req_id': rid, 'out_len': len(out),
                           'rounds': [{'r': x['r'], 'pos': x['pos'], 'committed': x['committed_raw']} for x in Ar[rid]]}
else:
    i = 0
    for rid in order:
        a, b = A[rid]['output_ids'], B[rid]['output_ids']
        if a == b: continue
        d = 0
        while d < min(len(a), len(b)) and a[d] == b[d]: d += 1
        inp = A[rid]['prompt_ids']; xa, xb = covering(Ar[rid], d), covering(Br[rid], d)
        w = f"W 2 {a[d]} {b[d]}"
        tag = f"div{i}"
        form_i(J, f"{tag}_i", inp, a, d, False); J.insert(len(J) - d - 1, w)
        form_round(J, f"{tag}_ii", inp, a, xa); J.insert(len(J) - 2, w)
        form_round(J, f"{tag}_iii", inp, b, xb); J.insert(len(J) - 2, w)
        k = len(J); form_hist(J, f"{tag}_iv", inp, a, Ar[rid], xa['r']); J.insert(k + 1, w)
        k = len(J); form_hist(J, f"{tag}_v", inp, b, Br[rid], xb['r']); J.insert(k + 1, w)
        meta[tag] = {'req_id': rid, 'd': d, 'tokA': a[d], 'tokB': b[d], 'plen': len(inp),
                     'A_round': {'r': xa['r'], 'pos': xa['pos'], 'T': xa['T'], 'row': d - xa['pos'], 'vmargin': xa['vmargin'][d - xa['pos']]},
                     'B_round': {'r': xb['r'], 'pos': xb['pos'], 'T': xb['T'], 'row': d - xb['pos'], 'vmargin': xb['vmargin'][d - xb['pos']]},
                     'A_hist_vmargin': {x['r']: x['vmargin'] for x in Ar[rid] if x['r'] <= xa['r']},
                     'B_hist_vmargin': {x['r']: x['vmargin'] for x in Br[rid] if x['r'] <= xb['r']}}
        i += 1
open(sys.argv[4], 'w').write('\n'.join(J) + '\n')
json.dump(meta, open(sys.argv[4] + '.meta.json', 'w'), indent=1)
print(len([j for j in J if j.startswith('J ')]), 'jobs', len(J), 'steps')
