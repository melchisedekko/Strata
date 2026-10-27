#!/usr/bin/env python3
"""proxy CPU, non AMD, llama.cpp non Strata. A/B tok/s (a') vs default (a) a coppie alternate (runs/live_combo_aprime_holdout_v3.md).
Scritto il 27/10/2026, NON ancora eseguito su dati reali. Non lancia processi llama: legge solo i .jsonl del tracer v14.
Modi:
  greedy OUT.json F1.jsonl F2.jsonl ...   output_ids per req_id identici in TUTTI i file (tutte le ripetizioni dei due bracci).
                                          exit 0 = tutto identico, 1 = almeno un prompt diverso (regola (ii): ferma tutto), 2 = errore.
  ab OUT.json A1,A2,.. B1,B2,..           tok/s per richiesta = output_tokens / (decode_ms/1000) (prefill escluso). Coppie (Ai,Bi) nell'ordine dato.
                                          Per dominio: metrica = somma token / somma decode_ms medio per prompt (somma/somma), per braccio;
                                          guadagno = tok/s(A)/tok/s(B) - 1; IC95 bootstrap percentile per prompt (10000 ricampionamenti, seed 20261027);
                                          varianza: guadagno per coppia (ogni coppia i separatamente), deviazione standard fra coppie, CV per braccio fra ripetizioni.
                                          OUT.json = solo aggregati per dominio; OUT.perprompt.json = valori per prompt (il chiamante lo nomina col tag edit).
  decide OUT.json AB1.json AB2.json POST1.json POST2.json VAL1.json VAL2.json
                                          applica le soglie (i)-(iv) del .md. Riferimento del replay per (i): env POLICY_REPLAY_REF (JSON con
                                          {"AL": {dominio: AL somma/somma}}) e POLICY_REPLAY_REF_SHA256; se assente o sha diverso, (i) = non valutabile."""
import json, sys, os, random, hashlib, time, statistics
LABEL = 'proxy CPU, non AMD, llama.cpp non Strata'
SEED, NBOOT = 20261027, 10000
def reqs(f):
    out = {}
    for l in open(f):
        if '"request"' not in l: continue
        try: j = json.loads(l)
        except ValueError: continue
        if j.get('type') == 'request': out[j['req_id']] = j
    return out
def sha(f): return hashlib.sha256(open(f, 'rb').read()).hexdigest()
def greedy(o, files):
    R = [reqs(f) for f in files]; keys = sorted(set().union(*R)); diff = []; missing = []
    for k in keys:
        outs = [r[k].get('output_ids') if k in r else None for r in R]
        if any(x is None for x in outs): missing.append(k); continue
        if any(x != outs[0] for x in outs[1:]): diff.append(k)
    res = {'label': LABEL, 'created': time.strftime('%F %T %Z'), 'files': {f: sha(f) for f in files}, 'prompts': len(keys),
           'identical': len(keys) - len(diff) - len(missing), 'differs': diff, 'missing': missing, 'all_identical': not diff and not missing}
    json.dump(res, open(o, 'w'), indent=1); print(json.dumps({k: res[k] for k in ('prompts', 'identical', 'all_identical')}))
    return 0 if res['all_identical'] else 1
def pct(xs, q):
    xs = sorted(xs); i = q * (len(xs) - 1); lo = int(i); hi = min(lo + 1, len(xs) - 1); return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)
def ab(o, fa, fb):
    A = [reqs(f) for f in fa.split(',')]; B = [reqs(f) for f in fb.split(',')]
    if len(A) != len(B) or not A: raise SystemExit('servono coppie (stesso numero di file A e B)')
    keys = sorted(set.intersection(*[set(r) for r in A + B])); dom = {}
    for k in keys: dom.setdefault(A[0][k].get('domain'), []).append(k)
    agg = {}; per = {}
    for d, ks in sorted(dom.items(), key=lambda x: str(x[0])):
        tok = {k: A[0][k]['output_tokens'] for k in ks}
        ta = {k: statistics.mean(r[k]['decode_ms'] for r in A) for k in ks}; tb = {k: statistics.mean(r[k]['decode_ms'] for r in B) for k in ks}
        def gain(sel, xa=ta, xb=tb):
            n = sum(tok[k] for k in sel); return (n / sum(xa[k] for k in sel)) / (n / sum(xb[k] for k in sel)) - 1
        rng = random.Random(SEED); boot = [gain([rng.choice(ks) for _ in ks]) for _ in range(NBOOT)]
        pair = [gain(ks, {k: A[i][k]['decode_ms'] for k in ks}, {k: B[i][k]['decode_ms'] for k in ks}) for i in range(len(A))]
        def tps(R): return [sum(tok[k] for k in ks) / sum(r[k]['decode_ms'] for k in ks) * 1000 for r in R]
        sa, sb = tps(A), tps(B)
        agg[str(d)] = {'prompts': len(ks), 'pairs': len(A), 'tok_s_A_sumsum': round(sum(tok.values()) / sum(ta.values()) * 1000, 4),
                       'tok_s_B_sumsum': round(sum(tok.values()) / sum(tb.values()) * 1000, 4), 'gain': round(gain(ks), 6),
                       'ci95_bootstrap_per_prompt': [round(pct(boot, 0.025), 6), round(pct(boot, 0.975), 6)],
                       'gain_per_pair': [round(x, 6) for x in pair], 'gain_pair_sd': round(statistics.stdev(pair), 6) if len(pair) > 1 else None,
                       'tok_s_per_rep_A': [round(x, 4) for x in sa], 'tok_s_per_rep_B': [round(x, 4) for x in sb],
                       'cv_rep_A': round(statistics.stdev(sa) / statistics.mean(sa), 6) if len(sa) > 1 else None,
                       'cv_rep_B': round(statistics.stdev(sb) / statistics.mean(sb), 6) if len(sb) > 1 else None,
                       'output_tokens_equal_A_B': all(A[0][k]['output_tokens'] == B[0][k]['output_tokens'] for k in ks)}
        per[str(d)] = {k: {'tokens': tok[k], 'decode_ms_A': [r[k]['decode_ms'] for r in A], 'decode_ms_B': [r[k]['decode_ms'] for r in B]} for k in ks}
    meta = {'label': LABEL, 'created': time.strftime('%F %T %Z'), 'A': {f: sha(f) for f in fa.split(',')}, 'B': {f: sha(f) for f in fb.split(',')},
            'seed': SEED, 'nboot': NBOOT, 'metric': 'tok/s = output_tokens/decode_ms (prefill escluso), somma/somma per dominio, decode_ms medio fra ripetizioni'}
    json.dump(dict(meta, domains=agg), open(o, 'w'), indent=1)
    json.dump(dict(meta, per_prompt=per), open(o[:-5] + '.perprompt.json', 'w'), indent=1)
    print(json.dumps({d: {k: v[k] for k in ('gain', 'ci95_bootstrap_per_prompt')} for d, v in agg.items()})); return 0
def decide(o, ab1, ab2, p1, p2, v1, v2):
    AB = {}; [AB.update(json.load(open(f))['domains']) for f in (ab1, ab2)]
    P = [json.load(open(f)) for f in (p1, p2)]; V = [json.load(open(f)) for f in (v1, v2)]
    validity = all(v['all_pairs']['all_100pct'] for v in V)
    coher = all(p[a]['coherence']['pass_ge_99pct'] for p in P for a in ('aprime', 'default_a'))
    greedy_ok = all(p['greedy_identical_aprime_vs_default']['identical'] == p['greedy_identical_aprime_vs_default']['common'] for p in P)
    al = {}; [al.update({d: x['sumsum_all'] for d, x in p['aprime']['AL'].items()}) for p in P]
    ref, refp, refs = None, os.environ.get('POLICY_REPLAY_REF'), os.environ.get('POLICY_REPLAY_REF_SHA256')
    if refp and refs and os.path.exists(refp) and sha(refp) == refs: ref = json.load(open(refp))['AL']
    dev = {d: round(al[d] / ref[d] - 1, 6) for d in al if ref and d in ref}
    code_d = [d for d in AB if 'code' in d and 'edit' not in d]; edit_d = [d for d in AB if 'edit' in d]; chat_d = [d for d in AB if 'chat' in d]
    pm3 = bool(ref) and all(abs(dev.get(d, 9)) <= 0.03 for d in code_d + edit_d)
    i_ok = validity and coher and pm3
    def go(ds): return bool(ds) and all(AB[d]['gain'] >= 0.03 and AB[d]['ci95_bootstrap_per_prompt'][0] > 0 for d in ds)
    iii = go(code_d) and go(edit_d) and bool(chat_d) and all(AB[d]['gain'] >= -0.01 for d in chat_d)
    res = {'label': LABEL, 'created': time.strftime('%F %T %Z'), 'inputs': {f: sha(f) for f in (ab1, ab2, p1, p2, v1, v2)},
           'policy_replay_ref': {'path': refp, 'sha256_expected': refs, 'used': ref is not None},
           'i': {'validity_cand_mtp_100pct': validity, 'coherence_ge_99pct': coher, 'al_dev_vs_replay': dev, 'within_3pct': pm3, 'pass': i_ok},
           'ii_greedy_aprime_vs_default_100pct': greedy_ok,
           'iii': {'gains': {d: {'gain': AB[d]['gain'], 'ci95': AB[d]['ci95_bootstrap_per_prompt']} for d in AB}, 'pass': iii},
           'GO_proxy': bool(i_ok and greedy_ok and iii), 'decides': bool(i_ok and greedy_ok),
           'iv': 'GO_proxy non cambia il default: con GO_proxy P0 va in testa alla misura AMD, senza GO_proxy resta in coda AMD'}
    json.dump(res, open(o, 'w'), indent=1); print(json.dumps({k: res[k] for k in ('GO_proxy', 'decides')})); return 0
if __name__ == '__main__':
    try:
        m = sys.argv[1]
        if m == 'greedy': sys.exit(greedy(sys.argv[2], sys.argv[3:]))
        if m == 'ab': sys.exit(ab(*sys.argv[2:5]))
        if m == 'decide': sys.exit(decide(*sys.argv[2:9]))
        raise SystemExit(2)
    except SystemExit: raise
    except Exception as e: print('errore:', e, file=sys.stderr); sys.exit(2)
