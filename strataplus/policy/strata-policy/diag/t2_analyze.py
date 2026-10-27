#!/usr/bin/env python3
"""proxy CPU, non AMD. arbiter_diag T2: τ dai prompt non divergenti e classificazione dei punti di divergenza (criteri di PREREG.md).
Uso: t2_analyze.py tau PROBE_tau.jsonl META_tau.json OUT.json
     t2_analyze.py div PROBE_div.jsonl META_div.json TAU OUT.json [TF.jsonl]
 τ: per ogni round di A1 e riga j < committed (contesto = output comune), |Δlogit top-1| = |l_(i)[t*] - l_(ii)[t*]|, t* = top-1 in (i).
 BUG per prompt: token di A1 in d non top-1 in nessuna forma testata, oppure margine (forma i) in d > 10·τ (T1 a parte).
 FP near-tie: margine (i) < τ  E  token A1 top-1 in una forma usata da A1 ((ii) o (iv))  E  token B1 top-1 in (iii)/(v) o in (i)."""
import json, sys, math
def rows(p):
    R = {}
    for l in open(p):
        x = json.loads(l); R.setdefault(x['job'], []).append(x)
    return R
def l_of(x, t):
    for a, v in x['top5'] + x['watch']:
        if a == t: return v
    return None
mode = sys.argv[1]; R = rows(sys.argv[2]); M = json.load(open(sys.argv[3]))
if mode == 'tau':
    D, Dg, miss = [], [], 0
    per = {}
    for k, m in M.items():
        ri = {x['pos']: x for x in R[f'{k}_i']}; plen1 = min(ri) ; n = 0
        for rd in m['rounds']:
            for x in R.get(f"{k}_ii_r{rd['r']}", []):
                j = x['row']
                if j >= rd['committed']: continue
                xi = ri.get(x['pos'])
                if xi is None: continue
                t = xi['top1']; v = l_of(x, t)
                if v is None: miss += 1; continue
                D.append(abs(xi['l1'] - v)); Dg.append(abs(xi['gap'] - x['gap']) if x['top1'] == t and x['top2'] == xi['top2'] else float('nan')); n += 1
        per[m['req_id']] = n
    D.sort(); p99 = D[min(len(D) - 1, math.ceil(0.99 * len(D)) - 1)]
    G = sorted(g for g in Dg if g == g)
    out = {'n_positions': len(D), 'per_prompt_positions': per, 'missing_top1_in_top5': miss, 'tau_max': D[-1], 'p99': p99,
           'median': D[len(D) // 2], 'n_exact_zero': sum(1 for d in D if d == 0.0),
           'gapdelta_max_same_top2': G[-1] if G else None, 'gapdelta_p99_same_top2': G[min(len(G) - 1, math.ceil(0.99 * len(G)) - 1)] if G else None}
    json.dump(out, open(sys.argv[4], 'w'), indent=1); print(json.dumps(out)); sys.exit()
tau = float(sys.argv[4]); out = {}
TF = {}
if len(sys.argv) > 6:
    for l in open(sys.argv[6]):
        x = json.loads(l)
        if x['type'] == 'round': TF.setdefault(x['req_id'], {})[x['pos']] = x['vmargin'][0]
for k, m in M.items():
    a, b = m['tokA'], m['tokB']; d = m['d']; res = {'req_id': m['req_id'], 'd': d, 'tokA': a, 'tokB': b}
    def pick(job, pos=None, rnd_row=None):
        L = R[job]
        if rnd_row is not None:   # ultimo batch registrato del job, riga data
            L = [x for x in L if x['step'] == max(y['step'] for y in L)]; return [x for x in L if x['row'] == rnd_row][0]
        return [x for x in L if x['pos'] == pos][-1]
    pos_d = m['plen'] - 1 + d
    F = {'i': pick(f'{k}_i', pos_d), 'ii': pick(f'{k}_ii', rnd_row=m['A_round']['row']), 'iii': pick(f'{k}_iii', rnd_row=m['B_round']['row']),
         'iv': pick(f'{k}_iv', rnd_row=m['A_round']['row']), 'v': pick(f'{k}_v', rnd_row=m['B_round']['row'])}
    for f, x in F.items():
        assert x['pos'] == pos_d, (k, f, x['pos'], pos_d)
        res[f] = {'top1': x['top1'], 'top2': x['top2'], 'margin': x['gap'], 'lA': l_of(x, a), 'lB': l_of(x, b)}
    # riproducibilità della storia esatta contro i vmargin loggati (tutti i round della storia)
    def hist_check(job, hv):
        L = R[job]; steps = sorted(set(x['step'] for x in L)); worst = 0.0; tokmis = 0; nrow = 0
        for s, (r, vm) in zip(steps, sorted(hv.items(), key=lambda z: int(z[0]))):
            for x in [y for y in L if y['step'] == s]:
                if x['row'] >= len(vm): continue
                t1, t2, g = vm[x['row']][:3]; nrow += 1
                tokmis += (t1 != x['top1']); worst = max(worst, abs(g - x['gap']))
        return {'rows': nrow, 'top1_mismatch': tokmis, 'max_abs_gap_diff': worst}
    res['iv_vs_log'] = hist_check(f'{k}_iv', m['A_hist_vmargin']); res['v_vs_log'] = hist_check(f'{k}_v', m['B_hist_vmargin'])
    res['A_log'] = m['A_round']['vmargin'][:3]; res['B_log'] = m['B_round']['vmargin'][:3]
    if m['req_id'] in TF and d in TF[m['req_id']]: res['TF_log'] = TF[m['req_id']][d][:3]
    mi = res['i']['margin']
    A_top1_any = any(res[f]['top1'] == a for f in F)
    bug = (not A_top1_any) or (mi > 10 * tau)
    fp = (mi < tau) and (res['ii']['top1'] == a or res['iv']['top1'] == a) and (res['iii']['top1'] == b or res['v']['top1'] == b or res['i']['top1'] == b)
    res['verdict'] = 'BUG' if bug else ('FP' if fp else 'INDETERMINATO')
    out[k] = res
json.dump(out, open(sys.argv[5], 'w'), indent=1)
for k, r in out.items():
    print(k, r['req_id'] if 'edit' not in sys.argv[2] else '-', r['d'], r['verdict'], 'mi=%.4f' % r['i']['margin'],
          ' '.join(f"{f}:{r[f]['top1']}/{r[f]['margin']:.4f}" for f in ['i', 'ii', 'iii', 'iv', 'v']), 'iv~log', r['iv_vs_log'], 'v~log', r['v_vs_log'])
