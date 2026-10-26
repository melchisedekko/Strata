#!/usr/bin/env python3
"""proxy CPU, non AMD. Diagnosi greedy v1.1: identita' allo stesso T (yright_T vs ywrong_T), confronto con T=1,
margini top1-top2 (logit e prob, softmax piena temp 1) del target nelle posizioni divergenti, ablazione LLAMAFILE=OFF.
Scrive traces/greedy_diag_v11.json e la sezione v1.1 in GREEDY_DIAG.md (sostituisce la sezione precedente v1.1 se c'e')."""
import json, os, glob, statistics as st
TR = '/workspace/strata-plus/traces'; RAW = f'{TR}/raw/v11'
def load(p):
    req, rounds = {}, {}
    if not os.path.exists(p): return None, None
    for l in open(p):
        j = json.loads(l)
        if j['type'] == 'request_end': req[j['req_id']] = j['output_ids']
        elif j['type'] == 'round': rounds.setdefault(j['req_id'], []).append(j)
    return req, rounds
def fdiv(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y: return i
    return None if len(a) == len(b) else min(len(a), len(b))
def margin_at(rounds, p):
    """row of the round that predicts output index p: (T, row, top1, top2, logit_gap, p1, p2)"""
    for x in rounds:
        if x['source'] == 'replay': continue
        if x['pos'] <= p < x['pos'] + x['T']:
            m = x['vmargin'][p - x['pos']]
            return {'T': x['T'], 'row': p - x['pos'], 'top1': m[0], 'top2': m[1], 'gap_logit': m[2], 'p1': m[3], 'p2': m[4], 'gap_p': round(m[3] - m[4], 5)}
    return None
def pct(xs, q): xs = sorted(xs); return xs[min(len(xs) - 1, int(q * len(xs)))]
def main():
    base, brounds = load(f'{RAW}/base_p30.jsonl')
    res = {'same_T': {}, 'vs_T1': {}, 'margins': [], 'live_vs_T1': {}}
    for T in (2, 4, 8):
        yr, yrr = load(f'{RAW}/diag_yright_T{T}.jsonl'); yw, ywr = load(f'{RAW}/diag_ywrong_T{T}.jsonl')
        if not yr or not yw: continue
        ids = [i for i in yr if i in yw]
        res['same_T'][T] = {i: fdiv(yr[i], yw[i]) for i in ids}
        res['vs_T1'][T] = {i: {'yright': fdiv(yr[i], base[i]), 'ywrong': fdiv(yw[i], base[i])} for i in ids}
        for i in ids:
            for kind, out, rr in (('yright', yr, yrr), ('ywrong', yw, ywr)):
                p = fdiv(out[i], base[i])
                if p is None or p >= len(base[i]): continue
                m1 = margin_at(brounds[i], p); mT = margin_at(rr[i], p)
                res['margins'].append({'req_id': i, 'T_run': T, 'kind': kind, 'pos': p, 'base_T1': m1, 'verify_T': mT,
                                       'y_token': base[i][p], 'run_token': out[i][p]})
    allgap = [x['vmargin'][0][2] for rr in brounds.values() for x in rr]
    allgp = [x['vmargin'][0][3] - x['vmargin'][0][4] for rr in brounds.values() for x in rr]
    res['all_positions_T1'] = {'n': len(allgap), 'gap_logit_p01': pct(allgap, .01), 'gap_logit_p05': pct(allgap, .05), 'gap_logit_median': st.median(allgap),
                               'gap_p_p01': pct(allgp, .01), 'gap_p_p05': pct(allgp, .05), 'frac_gap_logit_below_0.1': sum(g < 0.1 for g in allgap) / len(allgap)}
    for f in sorted(glob.glob(f'{RAW}/*live*.jsonl')):
        run = os.path.basename(f)[:-6]; o, _ = load(f)
        res['live_vs_T1'][run] = {i: fdiv(o[i], base[i]) for i in o if i in base}
    # ablation LLAMAFILE (ctx 512): base T=1 vs ywrong T=2 within the same build
    for n in ('llamafile_on', 'llamafile_off'):
        b, _ = load(f'{RAW}/abl_{n}_base.jsonl'); w, _ = load(f'{RAW}/abl_{n}_ywrong_T2.jsonl')
        if b and w: res.setdefault('ablation', {})[n] = {i: fdiv(w[i], b[i]) for i in w if i in b}
    json.dump(res, open(f'{TR}/greedy_diag_v11.json', 'w'), indent=1)
    L = ['## v1.1 (giro 02:34) — identità allo stesso T, margini, ablazione (proxy CPU, non AMD)', '',
         'Binario `proxy/llama_spec_trace.v11.bin`, flag `--no-repack --no-spec-draft-backend-sampling -t 6 -c 8192 -b 8192 -ub 512`, 12 prompt `diag_prompts.jsonl`. '
         'Riferimento T=1 = `raw/v11/base_p30` (stesso binario/flag). `yright_T`: draft = y (T fisso, tutto accettato); `ywrong_T`: draft = y con id+1 (T fisso, sempre rifiutato).', '',
         '### Identità allo stesso T (yright_T vs ywrong_T: stesso T, pattern di accettazione/rollback opposti)', '',
         '| prompt | ' + ' | '.join(f'T={T} yr≡yw | T={T} yr vs T1 | T={T} yw vs T1' for T in res['same_T']) + ' |',
         '|---|' + '---|---|---|' * len(res['same_T'])]
    ids = list(next(iter(res['same_T'].values())).keys()) if res['same_T'] else []
    f = lambda v: '=' if v is None else str(v)
    for i in ids:
        L.append(f'| {i} | ' + ' | '.join(f"{f(res['same_T'][T][i])} | {f(res['vs_T1'][T][i]['yright'])} | {f(res['vs_T1'][T][i]['ywrong'])}" for T in res['same_T']) + ' |')
    for T in res['same_T']:
        n_same = sum(v is None for v in res['same_T'][T].values()); n1 = sum(v['yright'] is not None for v in res['vs_T1'][T].values())
        L.append(f'\n- T={T}: yright≡ywrong su {n_same}/{len(ids)} prompt; yright ≠ T=1 su {n1}/{len(ids)}.')
    L += ['', '### Margini top1−top2 del target nelle posizioni divergenti', '',
          'Per ogni prima divergenza dal decode T=1: margine nel decode T=1 (riga 0 di base) e nella riga di verifica a T del run che diverge '
          '(gap_logit = l1−l2; p = softmax piena temp 1). Token top1/top2.', '',
          '| prompt | run | pos | T=1: top1/top2, gap_logit, p1−p2 | verify T: riga, top1/top2, gap_logit, p1−p2 |', '|---|---|---|---|---|']
    for m in res['margins']:
        a, b = m['base_T1'], m['verify_T']
        sa = f"{a['top1']}/{a['top2']}, {a['gap_logit']:.4f}, {a['gap_p']:.4f}" if a else '-'
        sb = f"r{b['row']}: {b['top1']}/{b['top2']}, {b['gap_logit']:.4f}, {b['gap_p']:.4f}" if b else '-'
        L.append(f"| {m['req_id']} | {m['kind']}_T{m['T_run']} | {m['pos']} | {sa} | {sb} |")
    g1 = [m['base_T1']['gap_logit'] for m in res['margins'] if m['base_T1']]
    gT = [m['verify_T']['gap_logit'] for m in res['margins'] if m['verify_T']]
    a = res['all_positions_T1']
    if g1:
        L += ['', f"- Gap logit nel decode T=1 alle posizioni divergenti: n={len(g1)}, mediana {st.median(g1):.4f}, max {max(g1):.4f}; "
              f"alla verifica T: mediana {st.median(gT):.4f}, max {max(gT):.4f}.",
              f"- Tutte le posizioni del decode T=1 (n={a['n']}): gap logit p1 {a['gap_logit_p01']:.4f}, p5 {a['gap_logit_p05']:.4f}, mediana {a['gap_logit_median']:.4f}; "
              f"quota con gap<0.1: {a['frac_gap_logit_below_0.1']:.4f}."]
    if 'ablation' in res:
        L += ['', '### Ablazione: build `-DGGML_LLAMAFILE=OFF` (dir separata `build-nollamafile`), verify T=2 (ywrong), `-c 512`', '',
              'Confronto entro la stessa build: output di ywrong_T2 vs decode T=1 della stessa build (prompt che non entrano in 512 posizioni sono saltati).', '',
              '| prompt | LLAMAFILE ON | LLAMAFILE OFF |', '|---|---|---|']
        ab = res['ablation']; keys = sorted(set().union(*[set(v) for v in ab.values()]))
        for i in keys: L.append(f"| {i} | {f(ab.get('llamafile_on', {}).get(i, '-'))} | {f(ab.get('llamafile_off', {}).get(i, '-'))} |")
        for n, v in ab.items(): L.append(f"\n- {n}: divergenti {sum(x is not None for x in v.values())}/{len(v)}")
    md = open(f'{TR}/GREEDY_DIAG.md').read().split('\n## v1.1 (giro 02:34)')[0].rstrip() + '\n\n' + '\n'.join(L) + '\n'
    open(f'{TR}/GREEDY_DIAG.md', 'w').write(md); print('\n'.join(L[-30:]))
if __name__ == '__main__': main()
