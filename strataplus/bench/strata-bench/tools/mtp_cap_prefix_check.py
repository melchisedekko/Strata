#!/usr/bin/env python3
"""proxy CPU, non AMD. Pre-check indipendenza dal cap del draft MTP (llama.cpp draft-mtp, greedy, --spec-draft-p-min default 0.0 =
nessun troncamento per probabilita': llama.cpp common/common.h L333, common/speculative.cpp L1868-1873). Per coppie di trace (A, B) sugli
stessi prompt: per ogni posizione di output g in cui entrambe hanno un round non-replay e il contesto e' identico (stessi prompt_ids e
output_A[:g] == output_B[:g]), confronta cand.mtp.tokens[:m] con m = min(len_A, len_B). Riporta coincidenti/totali e i casi divergenti.
Posizione: gen_index (schema v1.1) o somma dei committed dei round precedenti (schema v1). Nessuna metrica di tempo."""
import json, sys, hashlib, time, collections
def load(f):
    req = {}; rounds = collections.defaultdict(list); out = {}
    for l in open(f):
        j = json.loads(l); t = j.get('type'); k = (j.get('req_id'), j.get('rep', 0))
        if t == 'request': req[k] = j
        elif t == 'round': rounds[k].append(j)
        elif t == 'request_end': out[k] = j['output_ids']
    cand = {}
    for k, rs in rounds.items():
        g = 0; o = []; c = {}
        for r in rs:
            gi = r.get('gen_index', g)
            if r.get('source') != 'replay' and not r.get('partial_restore'):
                m = (r.get('cand') or {}).get('mtp') or {}
                c[gi] = (m.get('tokens') or [], m.get('probs') or [])
            cm = r.get('committed', 0)
            if cm > 0: o += r['target_tokens'][:cm]; g = gi + cm
        cand[k] = c
        if k not in out: out[k] = o
    return req, cand, out
def pid(j):
    if 'prompt_ids' in j: return hashlib.sha256(json.dumps(j['prompt_ids']).encode()).hexdigest()
    return j.get('prompt_sha256')
def compare(fa, fb):
    ra, ca, oa = load(fa); rb, cb, ob = load(fb); tot = eq = 0; div = []; firstidx = collections.Counter(); skipped_ctx = 0; nreq = 0; maxdp = 0.0
    for k in sorted(set(ca) & set(cb)):
        if k not in ra or k not in rb or pid(ra[k]) != pid(rb[k]): continue
        nreq += 1
        for g in sorted(set(ca[k]) & set(cb[k])):
            if oa[k][:g] != ob[k][:g] or len(oa[k]) < g or len(ob[k]) < g: skipped_ctx += 1; continue
            ta, pa = ca[k][g]; tb, pb = cb[k][g]; m = min(len(ta), len(tb))
            if m == 0: continue
            tot += 1
            if ta[:m] == tb[:m]:
                eq += 1
                for x, y in zip(pa[:m], pb[:m]): maxdp = max(maxdp, abs(x - y))
            else:
                fi = next(i for i in range(m) if ta[i] != tb[i]); firstidx[fi] += 1
                if len(div) < 50: div.append({'req_id': k[0], 'rep': k[1], 'gen_index': g, 'A': ta[:m], 'B': tb[:m], 'A_probs': pa[:m], 'B_probs': pb[:m]})
    return {'A': fa, 'B': fb, 'A_sha256': hashlib.sha256(open(fa, 'rb').read()).hexdigest(), 'B_sha256': hashlib.sha256(open(fb, 'rb').read()).hexdigest(),
            'requests_compared': nreq, 'positions_same_context': tot, 'coincident': eq, 'divergent': tot - eq,
            'coincident_frac': round(eq / tot, 6) if tot else None, 'positions_skipped_context_differs': skipped_ctx,
            'max_abs_prob_diff_on_coincident': round(maxdp, 6), 'divergent_by_first_differing_index': {str(i): firstidx[i] for i in sorted(firstidx)}, 'divergent_cases_first50': div}
if __name__ == '__main__':
    out = sys.argv[1]; pairs = [p.split(':') for p in sys.argv[2:]]
    res = {'label': 'proxy CPU, non AMD', 'created': time.strftime('%F %T %Z'), 'doc': __doc__, 'pairs': [compare(a, b) for a, b in pairs]}
    tot = sum(p['positions_same_context'] for p in res['pairs']); eq = sum(p['coincident'] for p in res['pairs'])
    res['all_pairs'] = {'positions_same_context': tot, 'coincident': eq, 'coincident_frac': round(eq / tot, 6) if tot else None, 'all_100pct': all(p['divergent'] == 0 for p in res['pairs'])}
    json.dump(res, open(out, 'w'), indent=1)
    for p in res['pairs']: print(p['A'].split('/')[-1], 'vs', p['B'].split('/')[-1], p['requests_compared'], p['coincident'], '/', p['positions_same_context'], 'skipped', p['positions_skipped_context_differs'], 'maxdp', p['max_abs_prob_diff_on_coincident'])
    print(res['all_pairs'])
