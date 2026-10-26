#!/usr/bin/env python3
"""proxy CPU, non AMD. Divergenza traiettoria live vs teacher-forced (TF) e AL live vs replay TF dello stesso algoritmo.
Uso: check_v12_divergence.py <dir_tracce> <prefisso_run> <out.json>   (es. traces/check_v12 check_v12 out.json)
Per ogni richiesta e per ogni run live (mtp_k3, lookup, combo):
 first_divergence_pos = primo indice i con live.output_ids[i] != tf.output_ids[i] (se una e' prefisso dell'altra: min(len)); null se identiche.
 AL_live_full = mean(min(accepted+1, committed)) [agent_v12: committed gia limitato all EOS da clamp_eos_agent_v12.py] su tutti i round; AL_live_pre_div = idem sui round con pos+committed <= first_divergence_pos (tutti se null).
 Replay TF: simulazione deterministica della stessa regola sulla traiettoria TF, usando i candidati registrati nel TF a ogni posizione p
 (draft MTP Dmax=7 e candidato lookup, Dmax=7): rem = len(y)-p-1 (token rimasti), accettati = lcp(draft[:k], y[p:p+k]), avanzamento accettati+1.
   mtp_k3: k=min(3,rem). lookup: k=min(len(lookup),rem), k=0 -> round T=1. combo: regola di proxy/llama_spec_trace.cpp:322
   (lookup se len(lookup)>0, k_mtp>0, lookup[0]==mtp[0] e len(lookup)>k_mtp, con k_mtp=min(3,rem); altrimenti MTP k_mtp).
 AL_replay_full e AL_replay_pre_div (round simulati con p+accettati+1 <= first_divergence_pos).
 Nessuna metrica A/B: solo AL di controllo (tolleranza 2%) e divergenza."""
import json, sys, os, collections, hashlib, time
D, PFX, OUT = sys.argv[1:4]
def load(f):
    req, rounds, end = {}, collections.defaultdict(list), {}
    for l in open(f):
        j = json.loads(l)
        if j.get('type') == 'header': continue
        k = (j['req_id'], j.get('rep', 0))
        if j['type'] == 'request': req[k] = j
        elif j['type'] == 'round': rounds[k].append(j)
        elif j['type'] == 'request_end': end[k] = j
    return req, rounds, end
def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y: break
        n += 1
    return n
def replay(rows, y, alg):
    byp = {r['pos']: r for r in rows}; p = 0; out = []
    while p < len(y):
        r = byp.get(p)
        if r is None: return None, p
        rem = len(y) - p - 1; m = (r['cand'].get('mtp') or {}).get('tokens') or []; L = (r['cand'].get('lookup') or {}).get('tokens') or []
        if alg == 'mtp_k3': d = m[:min(3, rem)]
        elif alg == 'lookup': d = L[:min(len(L), rem)]
        else:
            km = min(3, rem); d = m[:km]
            if L and km > 0 and m and L[0] == m[0] and len(L) > km: d = L[:min(len(L), rem)]
        a = lcp(d, y[p:p + len(d)]); out.append((p, a)); p += a + 1
    return out, None
tf_req, tf_rounds, tf_end = load(f'{D}/{PFX}_tf_d7.jsonl')
res = {'label': 'proxy CPU, non AMD', 'created': time.strftime('%F %T %Z'), 'doc': __doc__, 'tf_file': f'{D}/{PFX}_tf_d7.jsonl',
       'tf_sha256': hashlib.sha256(open(f'{D}/{PFX}_tf_d7.jsonl', 'rb').read()).hexdigest(), 'runs': {}}
for alg in ('mtp_k3', 'lookup', 'combo'):
    f = f'{D}/{PFX}_live_{alg}.jsonl'
    if not os.path.exists(f): continue
    lreq, lrounds, lend = load(f); per = []
    agg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for k in sorted(lreq):
        y = tf_end[k]['output_ids']; o = lend[k]['output_ids']; dom = lreq[k].get('domain')
        dv = lcp(o, y); dv = None if (dv == len(o) == len(y)) else dv
        lim = dv if dv is not None else 10**9
        lv = [(r['pos'], r['accepted'], r['committed']) for r in lrounds[k]]
        rp, miss = replay(tf_rounds[k], y, alg)
        row = {'req_id': k[0], 'rep': k[1], 'domain': dom, 'output_tokens_live': len(o), 'output_tokens_tf': len(y), 'first_divergence_pos': dv}
        sets = {'live_full': [(min(a + 1, c) if c > 0 else a + 1) for _, a, c in lv], 'live_pre_div': [(min(a + 1, c) if c > 0 else a + 1) for p, a, c in lv if p + c <= lim]}
        if rp is not None:
            sets['replay_full'] = [a + 1 for _, a in rp]; sets['replay_pre_div'] = [a + 1 for p, a in rp if p + a + 1 <= lim]
        else: row['replay_missing_pos'] = miss
        for s, v in sets.items():
            row[f'AL_{s}'] = round(sum(v) / len(v), 4) if v else None; row[f'rounds_{s}'] = len(v)
            for g in (dom, 'ALL'): agg[g][s][0] += sum(v); agg[g][s][1] += len(v)
        per.append(row)
    summ = {}
    for g, d in agg.items():
        s = {f'AL_{n}': round(a / b, 4) if b else None for n, (a, b) in d.items()}; s.update({f'rounds_{n}': b for n, (a, b) in d.items()})
        for w in ('full', 'pre_div'):
            if s.get(f'AL_live_{w}') and s.get(f'AL_replay_{w}'):
                s[f'rel_diff_live_vs_replay_{w}'] = round(s[f'AL_live_{w}'] / s[f'AL_replay_{w}'] - 1, 5)
                s[f'within_2pct_{w}'] = abs(s[f'rel_diff_live_vs_replay_{w}']) <= 0.02
        summ[g] = s
    nd = sum(r['first_divergence_pos'] is not None for r in per)
    res['runs'][alg] = {'live_file': f, 'live_sha256': hashlib.sha256(open(f, 'rb').read()).hexdigest(), 'requests': len(per),
                        'requests_diverged': nd, 'requests_identical': len(per) - nd, 'summary': dict(sorted(summ.items())), 'per_request': per}
json.dump(res, open(OUT, 'w'), indent=1)
for a, r in res['runs'].items(): print(a, r['requests'], 'diverged', r['requests_diverged'], json.dumps(r['summary']['ALL']))
