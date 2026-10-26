#!/usr/bin/env python3
"""proxy CPU, non numeri AMD. Riepilogo delle tracce strataplus.v1 in /workspace/strata-plus/traces/*.jsonl.
Scrive SUMMARY.md e summary.json. I tempi CPU servono solo per rapporti relativi (speedup), mai come tok/s AMD."""
import glob, json, math, os, re, statistics as st
from collections import defaultdict

TR = '/workspace/strata-plus/traces'
DOMS = ['code', 'chat', 'edit']

def load(run):
    reqs, rounds = {}, defaultdict(list)
    for l in open(f'{TR}/{run}.jsonl'):
        j = json.loads(l)
        if j['type'] == 'request': reqs[j['req_id']] = j
        else: rounds[j['req_id']].append(j)
    return reqs, rounds

def ci95(xs):
    if len(xs) < 2: return [None, None]
    m, s = st.mean(xs), st.stdev(xs); h = 1.96 * s / math.sqrt(len(xs))
    return [round(m - h, 4), round(m + h, 4)]

def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y: break
        n += 1
    return n

def main():
    runs = sorted(os.path.basename(f)[:-6] for f in glob.glob(f'{TR}/*.jsonl'))
    S = {'label': 'proxy CPU, non numeri AMD', 'configs': {}, 'tf': {}, 'v1': {}, 'path_independence': {}}
    data = {r: load(r) for r in runs}
    # ---- live configs: AL per domain, speedup vs base of the same rep, greedy equality
    fam = defaultdict(list)
    for r in runs:
        m = re.match(r'(base|live_[a-z0-9_]+?)_r(\d)$', r)
        if m: fam[m.group(1)].append((int(m.group(2)), r))
    for f, lst in sorted(fam.items()):
        rec = {'reps': len(lst), 'by_domain': {}, 'greedy_equal': 0, 'requests': 0}
        sp_all = defaultdict(list); sp_rob = defaultdict(list); al_dom = defaultdict(lambda: [0, 0]); src_cnt = defaultdict(int)
        km = re.search(r'_k(\d+)$', f); kcfg = int(km.group(1)) if km else None
        n_endcap = 0; outliers = []
        def med_run(rr): return st.median(q['stats']['decode_ms'] for q in data[rr][0].values())
        for rep, r in lst:
            reqs, rounds = data[r]
            base = data.get(f'base_r{rep}', (None,))[0]
            for rid, q in reqs.items():
                rec['requests'] += 1; rec['greedy_equal'] += bool(q['greedy_equal_ref'])
                d = q['domain']
                vr = [x for x in rounds[rid] if x['source'] != 'replay']
                # artefatto del proxy: all'ultimo round n_draft_max=0 -> dp.n_max=0 = "nessun cap" e l'MTP drafta a
                # params.n_max=7 (oltre k). Questi round sono esclusi dall'AL e contati a parte.
                if kcfg is not None:
                    bad = [x for x in vr if x['source'] == 'mtp' and x['k_proposed'] > kcfg]
                    n_endcap += len(bad); vr = [x for x in vr if not (x['source'] == 'mtp' and x['k_proposed'] > kcfg)]
                al_dom[d][0] += sum(x['committed'] for x in vr); al_dom[d][1] += len(vr)
                for x in vr: src_cnt[x['source']] += 1
                if base and rid in base:
                    sp = base[rid]['stats']['decode_ms'] / q['stats']['decode_ms']
                    sp_all[d].append(sp); sp_all['all'].append(sp)
                    # outlier di sistema: decode_ms > 2x la mediana della propria run (stalli esterni, carico di altri processi)
                    ob = base[rid]['stats']['decode_ms'] > 2 * med_run(f'base_r{rep}')
                    if ob: outliers.append(f'base_r{rep}:{rid}')
                    else: sp_rob[d].append(sp); sp_rob['all'].append(sp)
        for d in DOMS + ['all']:
            if d == 'all':
                c = sum(al_dom[x][0] for x in DOMS); n = sum(al_dom[x][1] for x in DOMS)
            else:
                c, n = al_dom[d]
            sp = sp_all[d]
            rec['by_domain'][d] = {'AL_tokens_per_verify': round(c / n, 4) if n else None, 'verify_rounds': n,
                                   'speedup_cpu_mean': round(st.mean(sp), 4) if sp else None,
                                   'speedup_cpu_median': round(st.median(sp), 4) if sp else None,
                                   'speedup_cpu_std': round(st.stdev(sp), 4) if len(sp) > 1 else None,
                                   'speedup_cpu_ci95': ci95(sp), 'n': len(sp),
                                   'speedup_cpu_robust_mean': round(st.mean(sp_rob[d]), 4) if sp_rob[d] else None,
                                   'speedup_cpu_robust_ci95': ci95(sp_rob[d]), 'n_robust': len(sp_rob[d])}
        rec['sources'] = dict(src_cnt); rec['excluded_endcap_rounds'] = n_endcap; rec['speedup_outliers_excluded'] = sorted(set(outliers))
        divs = [q.get('first_divergence_pos') for rep, r in lst for q in data[r][0].values()]
        rec['first_divergence_pos'] = sorted(d for d in divs if d is not None)
        rec['greedy_equal_by_domain'] = {d: f"{sum(1 for rep, r in lst for q in data[r][0].values() if q['domain'] == d and q['greedy_equal_ref'])}/{sum(1 for rep, r in lst for q in data[r][0].values() if q['domain'] == d)}" for d in DOMS}
        S['configs'][f] = rec
    # per-rep speedup variance (mean over prompts per rep)
    # ---- teacher-forced: counterfactual acceptance of the full-depth candidates
    if 'tf_d7' in data:
        reqs, rounds = data['tf_d7']
        for d in DOMS + ['all']:
            am, al, has_l, agree, n = [], [], 0, [], 0
            depth = [0] * 8
            for rid, rr in rounds.items():
                if d != 'all' and reqs[rid]['domain'] != d: continue
                for x in rr:
                    n += 1
                    a = x['acc']['mtp']; am.append(a)
                    for j in range(1, 8): depth[j] += a >= j
                    if x['cand']['lookup']:
                        has_l += 1; al.append(x['acc']['lookup'])
                        agree.append(lcp(x['cand']['mtp']['tokens'], x['cand']['lookup']['tokens']))
            S['tf'][d] = {'positions': n, 'mtp_acc_mean_at_Dmax7': round(st.mean(am), 4),
                          'P_mtp_acc_ge_j': [round(depth[j] / n, 4) for j in range(1, 8)],
                          'lookup_coverage': round(has_l / n, 4), 'lookup_acc_mean_when_present': round(st.mean(al), 4) if al else None,
                          'lookup_acc_mean_all_positions': round(sum(al) / n, 4),
                          'mtp_lookup_agree_mean_when_both': round(st.mean(agree), 4) if agree else None}
        # ---- gate V1: fixed-k simulation on tf vs live AL
        tf_by = {rid: {x['pos']: x for x in rr} for rid, rr in rounds.items()}
        for k in [1, 2, 3, 5, 7]:
            run = f'live_mtp_k{k}_r0' if k != 3 else 'live_mtp_k3_r0'
            if run not in data: continue
            lreqs, lrounds = data[run]
            res = {}
            for subset in ('all', 'greedy_equal_only'):
                sim_c = sim_n = live_c = live_n = 0; match_rounds = cmp_rounds = 0; agree_tok = tot_tok = 0
                for rid, q in lreqs.items():
                    if subset == 'greedy_equal_only' and not q['greedy_equal_ref']: continue
                    y = q['ref_tokens']; N = len(y); pos = 0
                    while pos < N:
                        kk = max(0, min(k, N - pos - 1))   # same cap as the live loop (n_predict - n_predict_done - 1)
                        a = min(lcp(tf_by[rid][pos]['cand']['mtp']['tokens'][:kk], y[pos:]), kk)
                        sim_c += a + 1; sim_n += 1; pos += a + 1
                    vr = [x for x in lrounds[rid] if x['source'] != 'replay' and not (x['source'] == 'mtp' and x['k_proposed'] > k)]
                    live_c += sum(x['committed'] for x in vr); live_n += len(vr)
                    div = q.get('first_divergence_pos')
                    for x in vr:   # path independence: live MTP draft vs teacher-forced draft at the same pos (same prefix only)
                        t = tf_by[rid].get(x['pos'])
                        if t and x['cand']['mtp'] and (div is None or x['pos'] + len(x['cand']['mtp']['tokens']) <= div):
                            lt = x['cand']['mtp']['tokens']; tt = t['cand']['mtp']['tokens'][:len(lt)]
                            cmp_rounds += 1; match_rounds += lt == tt
                            agree_tok += sum(a == b for a, b in zip(lt, tt)); tot_tok += len(lt)
                res[subset] = {'requests': sum(1 for q in lreqs.values() if subset == 'all' or q['greedy_equal_ref']),
                               'AL_live': round(live_c / live_n, 4) if live_n else None,
                               'AL_sim_from_tf': round(sim_c / sim_n, 4) if sim_n else None,
                               'rounds_live': live_n, 'rounds_sim': sim_n,
                               'path_indep_rounds_compared': cmp_rounds,
                               'live_draft_identical_to_tf_draft_frac': round(match_rounds / cmp_rounds, 4) if cmp_rounds else None,
                               'token_agreement_frac': round(agree_tok / tot_tok, 4) if tot_tok else None}
            S['v1'][k] = res
    json.dump(S, open(f'{TR}/summary.json', 'w'), indent=1)
    # ---- markdown
    L = ['# Riepilogo tracce — **proxy CPU, non numeri AMD**', '',
         'Modello: Qwen3.5-2B-MTP Q4_K_M (llama.cpp CPU). AL = token committati per round di verifica (accepted+1). '
         'Speedup CPU = decode_ms(baseline, stessa ripetizione) / decode_ms(config), per prompt: solo rapporto relativo su CPU.', '',
         '',
         'Nomi config: `live_mtp_kK` = solo MTP, profondità K. `live_lookup` = solo lookup (SuffixDrafter di Strata), draft fino a Dmax=7. '
         '`live_combo_k3` = MTP k=3 **più** lookup fino a 7 token quando il lookup concorda col 1° token MTP ed è più lungo '
         '(regola tipo Strata, generate.cpp:16556-16563): per questo il suo AL può superare k+1=4 (nei round lookup T arriva a 8).', '',
         'Round esclusi dall\'AL: all\'ultimo round di una richiesta il proxy passa `dp.n_max=0` (= nessun cap) e l\'MTP drafta 7 token '
         'anche con k<7 (bug del proxy, solo ultimo round). Colonna "escl.". Speedup "robusto" = senza le coppie in cui la baseline '
         'ha decode_ms > 2× la mediana della sua run (stalli esterni; elenco in summary.json).', '',
         '## Config live', '', '| config | rip. | greedy = baseline | dominio | AL | escl. | speedup CPU media | mediana | std | IC95 | n | speedup robusto | IC95 robusto | n rob. |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for f, rec in S['configs'].items():
        for d in DOMS + ['all']:
            b = rec['by_domain'][d]
            L.append(f"| {f} | {rec['reps']} | {rec['greedy_equal']}/{rec['requests']} | {d} | {b['AL_tokens_per_verify']} | {rec['excluded_endcap_rounds'] if d == 'all' else ''} | {b['speedup_cpu_mean']} | {b['speedup_cpu_median']} | {b['speedup_cpu_std']} | {b['speedup_cpu_ci95']} | {b['n']} | {b['speedup_cpu_robust_mean']} | {b['speedup_cpu_robust_ci95']} | {b['n_robust']} |")
    L += ['', '### Uguaglianza greedy vs baseline base_r0 (per dominio) e prima posizione di divergenza', '', '| config | code | chat | edit | posizioni di divergenza |', '|---|---|---|---|---|']
    for f, rec in S['configs'].items():
        g = rec['greedy_equal_by_domain']
        L.append(f"| {f} | {g['code']} | {g['chat']} | {g['edit']} | {rec['first_divergence_pos']} |")
    if S['tf']:
        L += ['', '## Teacher-forced (tf_d7): candidate a profondità piena, accettazione controfattuale vs y', '',
              '| dominio | posizioni | acc MTP media (Dmax=7) | P(acc≥1..7) | copertura lookup | acc lookup (se c\'è) | acc lookup (tutte le pos.) | accordo MTP/lookup |', '|---|---|---|---|---|---|---|---|']
        for d, t in S['tf'].items():
            L.append(f"| {d} | {t['positions']} | {t['mtp_acc_mean_at_Dmax7']} | {t['P_mtp_acc_ge_j']} | {t['lookup_coverage']} | {t['lookup_acc_mean_when_present']} | {t['lookup_acc_mean_all_positions']} | {t['mtp_lookup_agree_mean_when_both']} |")
    if S['v1']:
        L += ['', '## Gate V1: simulatore k fisso (da tf_d7 + y) vs run live `--spec-draft-n-max k`', '',
              '| k | sottoinsieme | richieste | AL live | AL simulato | round live | round sim | round confrontati | draft live == draft tf | accordo token |', '|---|---|---|---|---|---|---|---|---|---|']
        for k, vv in S['v1'].items():
            for sub, v in vv.items():
                L.append(f"| {k} | {sub} | {v['requests']} | {v['AL_live']} | {v['AL_sim_from_tf']} | {v['rounds_live']} | {v['rounds_sim']} | {v['path_indep_rounds_compared']} | {v['live_draft_identical_to_tf_draft_frac']} | {v['token_agreement_frac']} |")
    if os.path.exists(f'{TR}/cost_p4_cpu.json'):
        p = json.load(open(f'{TR}/cost_p4_cpu.json'))
        L += ['', '## Profilo di costo P4 (proxy CPU, modello denso, non AMD)', '', '| modello | step_ms (T=1) | s(T) T=1..8 | rho_mtp (pendenza) [IC95] | rho_mtp (prof. 1) | rho_lu |', '|---|---|---|---|---|---|']
        for k, m in p['models'].items():
            L.append(f"| {k} | {m['step_ms']} | {m['s']} | {m.get('rho_mtp')} {m.get('rho_mtp_ci95')} | {m.get('rho_mtp_depth1')} | {m['rho_lu']} |")
    extra = []
    for f in ('CRITICAL.md', 'GREEDY_DIAG.md'):
        if os.path.exists(f'{TR}/{f}'): extra += [open(f'{TR}/{f}').read().rstrip(), '']
    L = L[:2] + extra + L[2:]
    open(f'{TR}/SUMMARY.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))

if __name__ == '__main__':
    main()
