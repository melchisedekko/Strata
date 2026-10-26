#!/usr/bin/env python3
"""proxy CPU, non AMD. Post-processing della run (a') vs default (a) con tracer v14 (runs/live_combo_aprime_holdout.md).
Nessuna misura di tempo. Calcola, per ciascun braccio:
 - coerenza: replay di proxy/strata_arbiter_v1.py sui candidati registrati (cand.mtp.probs, cand.lookup.tokens/match, room) e confronto
   con la scelta registrata (T e lookup); criterio >= 99% round identici, altrimenti il confronto +-3% non si legge;
 - AL live per round = min(accepted+1, committed) (committed gia' clampato a EOS dal tracer v14); per dominio: somma/somma (CRITERIO)
   e media per prompt delle AL per prompt (somma/somma interna); sia con tutti i round verify sia escludendo first_window;
 - greedy: output_ids identici fra i due bracci; greedy_equal_ref e first_divergence_pos da output_ids vs ref_tokens (--ref ref_holdout_tf.tsv);
   AL pre-divergenza = round con gen_index+committed <= first_divergence_pos.
Uso: aprime_post.py OUT.json APRIME.jsonl DEFAULT_A.jsonl"""
import json, sys, hashlib, collections, importlib.util, time, os
H = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('arb', os.path.join(H, '..', 'proxy', 'strata_arbiter_v1.py')); arb = importlib.util.module_from_spec(sp); sp.loader.exec_module(arb)
def load(f):
    req = {}; rounds = collections.defaultdict(list); order = []
    for l in open(f):
        j = json.loads(l); k = (j.get('req_id'), j.get('rep', 0))
        if j['type'] == 'request': req[k] = j
        elif j['type'] == 'round':
            if k not in rounds: order.append(k)
            rounds[k].append(j)
    return req, rounds, order
def arm(f):
    req, rounds, order = load(f); n = same = 0; fdiv = {}
    for k, j in req.items():
        o, rf = j.get('output_ids') or [], j.get('ref_tokens') or []; m = min(len(o), len(rf))
        fdiv[k] = next((i for i in range(m) if o[i] != rf[i]), None if len(o) == len(rf) else m); mism = []; al = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0]))
    for k in order:
        rs = [r for r in rounds[k] if r.get('source') != 'replay']; a0 = rs[0]['arbiter']
        A = arb.Arbiter(a0['S'])   # reset per prompt (generate.cpp L16429, CLI)
        for r in rs:
            a = r['arbiter']; c = r['cand']
            if a['first_window']: T, lk = 1, False
            else:
                lt = c['lookup']['tokens']; mt = c['mtp']['tokens']
                d = arb.decide(A, a['S'], a['S_mtp'], a['spec_min_p'], c['mtp']['probs'], min(len(lt), a['S'] - 1), c['lookup']['match'],
                               lt[0] if lt else -1, mt[0] if mt else -2, a['room'])
                T, lk = d['T'], d['lookup']
            n += 1
            if (T, lk) == (a['T'], a['lookup']): same += 1
            elif len(mism) < 50: mism.append({'req_id': k[0], 'r': r['r'], 'logged': [a['T'], a['lookup']], 'replay': [T, lk]})
            if a['observed'] and not a['first_window']: A.observe(a['lookup'], a['T'], r['accepted'], c['lookup']['match'])   # stato dalla scelta registrata
            v = min(r['accepted'] + 1, r['committed']); dom = r['domain']; s = al[dom][k[0]]
            s[0] += v; s[1] += 1
            if not a['first_window']: s[2] += v; s[3] += 1
            fd = fdiv.get(k)
            if fd is None or r['gen_index'] + r['committed'] <= fd: s[4] += v; s[5] += 1
    out = {'file': f, 'sha256': hashlib.sha256(open(f, 'rb').read()).hexdigest(), 'requests': len(order),
           'coherence': {'rounds': n, 'identical': same, 'frac': round(same / n, 6) if n else None, 'pass_ge_99pct': bool(n and same / n >= 0.99), 'mismatch_first50': mism},
           'greedy_equal_ref': {'true': sum(1 for v in fdiv.values() if v is None), 'n': len(req), 'first_divergence_pos': {k[0]: v for k, v in fdiv.items() if v is not None}}, 'AL': {}}
    for dom, d in sorted(al.items()):
        v = list(d.values())
        out['AL'][dom] = {'prompts': len(v), 'sumsum_all': round(sum(x[0] for x in v) / sum(x[1] for x in v), 6),
                          'mean_per_prompt_all': round(sum(x[0] / x[1] for x in v) / len(v), 6),
                          'sumsum_excl_first_window': round(sum(x[2] for x in v) / max(1, sum(x[3] for x in v)), 6),
                          'sumsum_pre_divergence': round(sum(x[4] for x in v) / max(1, sum(x[5] for x in v)), 6),
                          'mean_per_prompt_excl_first_window': round(sum(x[2] / x[3] for x in v if x[3]) / max(1, sum(1 for x in v if x[3])), 6)}
    return out, {k: hashlib.sha256(json.dumps(j.get('output_ids')).encode()).hexdigest() for k, j in req.items()}
if __name__ == '__main__':
    o, fa, fb = sys.argv[1:4]; ra, ha = arm(fa); rb, hb = arm(fb)
    common = sorted(set(ha) & set(hb)); eq = sum(1 for k in common if ha[k] == hb[k])
    res = {'label': 'proxy CPU, non AMD', 'created': time.strftime('%F %T %Z'), 'doc': __doc__, 'aprime': ra, 'default_a': rb,
           'greedy_identical_aprime_vs_default': {'common': len(common), 'identical': eq, 'differs': [k[0] for k in common if ha[k] != hb[k]]},
           'pm3pct_vs_policy_replay': 'NON calcolato qui: riferimento = run file di Strata Policy, da fissare'}
    json.dump(res, open(o, 'w'), indent=1); print(json.dumps({k: (v if k.startswith('greedy') else None) for k, v in res.items()}, default=str)[:600])
