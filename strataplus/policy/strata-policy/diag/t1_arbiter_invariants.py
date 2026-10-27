#!/usr/bin/env python3
"""proxy CPU, non AMD, llama.cpp non Strata. Strata Policy arbiter_diag T1 (solo tracce, nessun modello).
Per ogni round live del tracer v14 (llama_spec_trace_v14.cpp L310-483): rifà la decisione con proxy/strata_arbiter_v1.py
(stato ricostruito con observe() come L455) e controlla gli invarianti del percorso accetta/rifiuta/rollback.
Uso: t1_arbiter_invariants.py OUT_PERPROMPT_JSON TRACE.jsonl [TRACE.jsonl ...]   -> stampa aggregati JSON su stdout."""
import json, sys, importlib.util, collections
spec = importlib.util.spec_from_file_location('arb', '/workspace/strata-bench/proxy/strata_arbiter_v1.py')
arb = importlib.util.module_from_spec(spec); spec.loader.exec_module(arb)
N_CTX, N_PREDICT, DMAX, MTP_K = 8192, 128, 7, 3
import os
EOG = set(int(t) for t in os.environ.get('EOG_IDS', '248044,248046,248063,248064,248065').split(','))  # llama_vocab_is_eog del GGUF (verificati con logit_probe --eog)

def lcp(a, b):
    n = 0
    while n < len(a) and n < len(b) and a[n] == b[n]: n += 1
    return n

def check_file(path):
    rows = [json.loads(l) for l in open(path)]
    reqs = {}; order = []
    for x in rows:
        if x['type'] == 'round':
            if x['req_id'] not in reqs: reqs[x['req_id']] = {'rounds': []}; order.append(x['req_id'])
            reqs[x['req_id']]['rounds'].append(x)
        elif x['type'] == 'request': reqs.setdefault(x['req_id'], {'rounds': []})['req'] = x
    out = {}
    for rid in order:
        R = reqs[rid]['rounds']; q = reqs[rid]['req']
        a0 = R[0]['arbiter']; S, Smtp, minp = a0['S'], a0['S_mtp'], a0['spec_min_p']
        A = arb.Arbiter(S)
        viol = []; fields_ok = 0; n_dec = 0; minp_close = 0
        committed_out = []; prev = None
        plen = q['prompt_tokens']
        for x in R:
            r = x['r']; ab = x['arbiter']; prop = x['proposal']; tt = x['target_tokens']
            cm = x['cand']['mtp']; lkp = x['cand']['lookup']
            def V(msg): viol.append({'r': r, 'pos': x['pos'], 'what': msg})
            if x['source'] == 'replay' or x['partial_restore']: V('replay/partial_restore presente (non atteso: use_ckpt_tgt=false)')
            # --- posizioni / rollback
            if x['pos'] != len(committed_out): V(f"pos {x['pos']} != token committati finora {len(committed_out)}")
            if x['kv_pos'] != plen - 1 + x['pos']: V(f"kv_pos {x['kv_pos']} != prompt-1+pos {plen-1+x['pos']}")
            if x['ctx_len'] != x['kv_pos'] + 1: V('ctx_len != kv_pos+1')
            n_draft_max = max(min(N_CTX - x['kv_pos'] - 2, N_PREDICT - x['pos'] - 1), 0)
            # --- forma del round
            if len(prop) != x['T'] - 1 or x['k_proposed'] != len(prop): V('T/k_proposed incoerenti con proposal')
            if len(cm['tokens']) != min(MTP_K, n_draft_max): V(f"cand.mtp len {len(cm['tokens'])} != cap {min(MTP_K, n_draft_max)}")
            # --- accetta/rifiuta
            vm = x['vmargin']
            if len(vm) != len(prop) + 1: V('vmargin righe != T')
            argmax = [v[0] for v in vm]
            L = lcp(prop, argmax)  # prefisso del draft che coincide con l'argmax del target riga per riga
            for i in range(L):  # common_sampler_sample_and_accept_n (common/sampling.cpp L708): stop dopo un EOG accettato se i+1 < len(draft)
                if prop[i] in EOG and i + 1 < len(prop): L = i; break
            exp_ids = prop[:L] + [argmax[L]] if L < len(argmax) else prop[:L]
            eog_stop = L < len(prop) and prop[L] == argmax[L]
            if tt != exp_ids: V(f"target_tokens {tt} != prefisso accettato + correzione {exp_ids}")
            if len(tt) - 1 > len(prop): V('accettati oltre la lunghezza del draft')
            if tt[:len(tt) - 1] != prop[:len(tt) - 1]: V('token accettato diverso dal draft')
            if len(tt) - 1 < len(prop) and tt[-1] == prop[len(tt) - 1] and not (eog_stop and tt[-1] in EOG): V('correzione == token del draft (accettato oltre il primo mismatch?)')
            if x['committed_raw'] != len(tt): V('committed_raw != len(target_tokens)')
            if not x['eos_clamped']:
                if x['committed'] != len(tt) or x['accepted'] != len(tt) - 1: V('committed/accepted incoerenti (senza EOG)')
            else:
                if not (x['committed'] < len(tt) and x['accepted'] == min(len(tt) - 1, x['committed'])): V('clamp EOG incoerente')
            # --- arbitro
            if r == 0:
                exp = {'t_mtp': 1, 'gate': False, 'choose_called': False, 'lookup': False, 'T_pre_room': 1, 'T': 1}
                if not ab['first_window'] or ab['observed']: V('first_window/observed errati al round 0')
            else:
                k_full = len(lkp['tokens']); k_used = min(k_full, S - 1)
                if ab['k_full'] != k_full or ab['k_used'] != k_used or ab['match'] != lkp['match']: V('input lookup loggati incoerenti')
                if ab['room'] != 1 + n_draft_max: V(f"room {ab['room']} != 1+n_draft_max {1+n_draft_max}")
                if abs(ab['rounds_before'] - A.rounds) > 0.5: V(f"rounds_before {ab['rounds_before']} != replay {A.rounds}")
                if abs(ab['q'] - A.lookup_rate(lkp['match'])) > 5e-6: V('q loggato != replay')
                if minp > 0 and any(abs(p - minp) < 1e-5 for p in cm['probs']): minp_close += 1
                exp = arb.decide(A, S, Smtp, minp, cm['probs'], k_used, lkp['match'],
                                 lkp['tokens'][0] if k_full > 0 else -1, cm['tokens'][0] if cm['tokens'] else -2, 1 + n_draft_max)
            n_dec += 1
            same = all(ab[k] == exp[k] for k in ('t_mtp', 'gate', 'choose_called', 'lookup', 'T_pre_room', 'T'))
            fields_ok += same
            if not same: V(f"decisione arbitro: loggata {{{', '.join(f'{k}:{ab[k]}' for k in exp)}}} replay {exp}")
            # --- draft effettivamente verificato = fonte scelta, troncata a T-1
            src = lkp['tokens'] if ab['lookup'] else cm['tokens']
            if prop != src[:ab['T'] - 1]: V('proposal != fonte scelta[:T-1]')
            exp_src = ('lookup' if ab['lookup'] else 'mtp') if prop else 'none'
            if x['source'] != exp_src: V(f"source {x['source']} != {exp_src}")
            # --- observe come L455 (r>1 nel codice = round con indice >=1)
            if r >= 1: A.observe(ab['lookup'], ab['T'], x['accepted'], lkp['match'])
            committed_out += tt[:x['committed']]
            prev = x
        outp = q['output_ids']
        if committed_out[:N_PREDICT] != outp: viol.append({'r': None, 'pos': None, 'what': 'output_ids != concatenazione dei token committati'})
        out[rid] = {'domain': q['domain'], 'rounds': len(R), 'decisions_ok': fields_ok, 'decisions': n_dec,
                    'minp_within_1e-5': minp_close, 'violations': viol}
    return out

if __name__ == '__main__':
    allres = {}
    for p in sys.argv[2:]:
        allres[p] = check_file(p)
    json.dump(allres, open(sys.argv[1], 'w'), indent=1)
    agg = {}
    for p, res in allres.items():
        d = collections.defaultdict(lambda: collections.Counter())
        for rid, v in res.items():
            c = d[v['domain']]; c['prompts'] += 1; c['rounds'] += v['rounds']; c['dec_ok'] += v['decisions_ok']; c['dec'] += v['decisions']
            c['violations'] += len(v['violations']); c['prompts_with_viol'] += bool(v['violations']); c['minp_close'] += v['minp_within_1e-5']
        agg[p.split('/')[-1]] = {k: dict(c) for k, c in d.items()}
    print(json.dumps(agg, indent=1))
