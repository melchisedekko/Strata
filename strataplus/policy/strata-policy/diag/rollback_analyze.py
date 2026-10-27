#!/usr/bin/env python3
"""proxy CPU, non AMD. PREREG v2 Parte B: analisi dell'uscita di rollback_probe.
Uso: rollback_analyze.py OUT.jsonl JOBS.meta.json OUT.json [--control]   (--control: passata GGML_CPU_TILED_MM=0, validità solo seq_rm)
Criteri: PREREG_v2.md (sha256 72cac436…63a3) + addenda 1-3. τ = 0.566763."""
import json, sys, statistics as st
TAU = 0.566763
out_p, meta_p, res_p = sys.argv[1:4]; control = '--control' in sys.argv
meta = json.load(open(meta_p))
L, C, D, Rbad, init = {}, {}, {}, set(), None
lines = open(out_p).read().split('\n')
if lines and lines[-1] == '': lines.pop()
for n, line in enumerate(lines):
    try: x = json.loads(line)
    except json.JSONDecodeError:
        if n == len(lines) - 1: break  # riga finale ancora in scrittura
        raise
    if x['op'] == 'init': init = x
    elif x['op'] == 'L': L[x['key']] = x['rows']
    elif x['op'] == 'C': C[x['label']] = x
    elif x['op'] == 'D': D[x['label']] = x['rows']
    elif x['op'] == 'R' and not x['ok']: Rbad.add(x['job'])
def secmax(c): return max(v[2] for v in c['sec'].values()) if c.get('parsed') else (0.0 if c['bytes_equal'] else float('inf'))
recs = []
for m in meta:
    g, i = m['g'], m['r']; k = f"{g}|{i}"
    if any(f"{p}|{k}" not in D or f"{p}|{k}" not in C for p in ('aa', 'cc', 'ad', 'ab', 'ac')): recs.append({**m, 'missing': True}); continue
    rows = L[f"{g}_a_{i}"]; valid = f"{g}_a" not in Rbad and f"{g}_a2" not in Rbad and f"{g}_d_{i}" not in Rbad
    rep = all(r[0] == v[0] and abs(r[2] - v[2]) <= 1e-5 for r, v in zip(rows, m['q_vmargin'])) and len(rows) == len(m['q_vmargin'])
    if not control: valid = valid and rep
    rec = {**m, 'valid': valid, 'replay_ok': rep}; del rec['q_vmargin']
    for p in ('aa', 'cc', 'ad', 'ab', 'ac'):
        c, d = C[f"{p}|{k}"], D[f"{p}|{k}"]
        rec[p] = {'state_bytes_equal': c['bytes_equal'], 'meta_equal': c.get('meta_equal'), 'sec': c.get('sec'), 'state_max': secmax(c),
                  'row0': {'n_diff': d[0][1], 'max': d[0][2], 't1_a': d[0][3], 't1_ref': d[0][4], 'm_a': d[0][5], 'm_ref': d[0][6], 'dl1': abs(d[0][7] - d[0][8])},
                  'rows_max': max(r[2] for r in d), 'rows_ndiff': sum(r[1] for r in d)}
    recs.append(rec)
ok = [r for r in recs if not r.get('missing')]; V = [r for r in ok if r['valid']]
F_log = max([r[p]['rows_max'] for r in ok for p in ('aa', 'cc')] + [0.0])
F_state = max([r[p]['state_max'] for r in ok for p in ('aa', 'cc')] + [0.0])
def flip(r, p): return r[p]['row0']['t1_a'] != r[p]['row0']['t1_ref']
N1 = [r for r in V if r['ad']['state_max'] > F_state or r['ad']['meta_equal'] is False or r['ad']['row0']['max'] > F_log]
N2 = [r for r in V if any(flip(r, p) and r[p]['row0']['m_ref'] > TAU for p in ('ab', 'ac'))]
E1 = all(r['ad']['state_max'] <= F_state and r['ad']['meta_equal'] is not False and r['ad']['rows_max'] <= F_log for r in V)
E2 = all(not flip(r, p) or r[p]['row0']['m_ref'] <= TAU for r in V for p in ('ab', 'ac'))
E3 = all(r[p]['row0']['dl1'] <= TAU for r in V for p in ('ab', 'ac'))
frac_valid = len(V) / len(recs) if recs else 0
verdict = 'NON ESATTO' if (N1 or N2) else ('ESATTO' if (E1 and E2 and E3 and frac_valid >= 0.8) else 'INDETERMINATO')
def q(v):
    v = sorted(v); n = len(v)
    return {'n': n, 'max': v[-1], 'p99': v[min(n - 1, int(0.99 * n))], 'median': st.median(v)} if n else {'n': 0}
def summ(S):
    o = {'n_rounds': len(S)}
    for p in ('aa', 'cc', 'ad', 'ab', 'ac'):
        o[p] = {'state_bit_identical': sum(r[p]['state_bytes_equal'] for r in S), 'logits_row0_bit_identical': sum(r[p]['row0']['n_diff'] == 0 for r in S),
                'logits_allrows_bit_identical': sum(r[p]['rows_ndiff'] == 0 for r in S), 'row0_maxabs': q([r[p]['row0']['max'] for r in S]),
                'row0_dl1': q([r[p]['row0']['dl1'] for r in S]), 'row0_top1_flips': sum(flip(r, p) for r in S),
                'row0_top1_flips_ref_margin_gt_tau': sum(flip(r, p) and r[p]['row0']['m_ref'] > TAU for r in S),
                'flip_ref_margins': sorted(round(r[p]['row0']['m_ref'], 6) for r in S if flip(r, p)),
                'sec_max': {s: max([r[p]['sec'][s][2] for r in S if r[p]['sec']] + [0]) for s in ('kv_k', 'kv_v', 'conv', 'rec')},
                'sec_rounds_with_diff': {s: sum(1 for r in S if r[p]['sec'] and r[p]['sec'][s][1] > 0) for s in ('kv_k', 'kv_v', 'conv', 'rec')}}
    return o
res = {'init': init, 'control_tiled0': control, 'tau': TAU, 'n_tested': len(recs), 'n_missing': len(recs) - len(ok), 'n_valid': len(V),
       'n_replay_ok': sum(r['replay_ok'] for r in ok), 'n_seq_rm_false_jobs': len(Rbad), 'F_log': F_log, 'F_state': F_state,
       'N1': len(N1), 'N2': len(N2), 'E1': E1, 'E2': E2, 'E3': E3, 'frac_valid': frac_valid, 'verdict': verdict,
       'all': summ(V), 'by_arm': {a: summ([r for r in V if r['arm'] == a]) for a in ('A1', 'B1')},
       'strata': {'T_r<8': summ([r for r in V if r['T_r'] < 8]), 'T_r>=8': summ([r for r in V if r['T_r'] >= 8]),
                  'T_q=1': summ([r for r in V if r['T_q'] == 1]), 'T_q>=2': summ([r for r in V if r['T_q'] >= 2])},
       'per_prompt': {}, 'rounds': recs}
for rid in dict.fromkeys(m['req_id'] for m in meta):
    for a in ('A1', 'B1'):
        S = [r for r in V if r['req_id'] == rid and r['arm'] == a]; T = [r for r in recs if r['req_id'] == rid and r['arm'] == a]
        res['per_prompt'][f"{rid}|{a}"] = {'tested': len(T), 'valid': len(S), 'ad_state_bit': sum(r['ad']['state_bytes_equal'] for r in S),
            'ad_logits_bit': sum(r['ad']['rows_ndiff'] == 0 for r in S), 'ab_state_bit': sum(r['ab']['state_bytes_equal'] for r in S),
            'ac_state_bit': sum(r['ac']['state_bytes_equal'] for r in S),
            'ab_row0_max': max([r['ab']['row0']['max'] for r in S] + [0]), 'ac_row0_max': max([r['ac']['row0']['max'] for r in S] + [0]),
            'ab_dl1_max': max([r['ab']['row0']['dl1'] for r in S] + [0]), 'ac_dl1_max': max([r['ac']['row0']['dl1'] for r in S] + [0]),
            'ab_flips': sum(flip(r, 'ab') for r in S), 'ac_flips': sum(flip(r, 'ac') for r in S)}
json.dump(res, open(res_p, 'w'), indent=1)
print(json.dumps({k: res[k] for k in ('n_tested', 'n_missing', 'n_valid', 'n_replay_ok', 'n_seq_rm_false_jobs', 'F_log', 'F_state', 'N1', 'N2', 'E1', 'E2', 'E3', 'verdict')}))
