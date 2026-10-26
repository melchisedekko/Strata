#!/usr/bin/env python3
"""proxy CPU, modello denso, non AMD. Profilo di costo P4 (piano §4/§5, log_format D12) dai campioni p4 di
proxy/llama_spec_trace --mode p4. s(T)=mediana(verify T)/mediana(verify 1); rho_mtp = pendenza (ms per passo di draft
MTP, regressione sulle profondita' 1..Dmax) / mediana(verify 1); rho_lu = mediana(SuffixDrafter::propose) / mediana(verify 1).
IC 95% bootstrap (2000 ricampionamenti, seed 20261025) ricampionando i campioni per ripetizione."""
import json, sys, random, statistics as st, subprocess, platform

def boot(samples_by_key, fn, B=2000, seed=20261025):
    rnd = random.Random(seed); vals = []
    for _ in range(B):
        res = {k: [rnd.choice(v) for _ in v] for k, v in samples_by_key.items()}
        vals.append(fn(res))
    vals.sort()
    return [vals[int(0.025 * B)], vals[int(0.975 * B) - 1]]

def slope(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)

def analyse(path, dmax):
    v, d, lu = {}, {}, []
    ctxs = set()
    for l in open(path):
        j = json.loads(l)
        ctxs.add(j['ctx_len'])
        if j['what'] == 'verify': v.setdefault(j['T'], []).append(j['ms'])
        elif j['what'] == 'mtp_draft': d.setdefault(j['depth'], []).append(j['ms'])
        elif j['what'] == 'lookup': lu.append(j['ms'])
    med = lambda xs: st.median(xs)
    Ts = sorted(v)
    s_fn = lambda r: [med(r[T]) / med(r[1]) for T in Ts]
    s = s_fn(v)
    s_ci = boot(v, lambda r: tuple(s_fn(r)))  # tuple sort is lexicographic: compute per-T CI separately below
    s_ci = []
    for T in Ts:
        s_ci.append(boot({1: v[1], T: v[T]}, lambda r, T=T: med(r[T]) / med(r[1])))
    out = {'T': Ts, 's': [round(x, 4) for x in s], 's_ci95': [[round(a, 4), round(b, 4)] for a, b in s_ci],
           'verify_ms_median': {T: round(med(v[T]), 3) for T in Ts},
           'verify_ms_ci95': {T: [round(x, 3) for x in boot({0: v[T]}, lambda r: med(r[0]))] for T in Ts},
           'n_samples_per_T': {T: len(v[T]) for T in Ts}, 'step_ms': round(med(v[1]), 3), 'ctx_lens': sorted(ctxs)}
    if d:
        Ds = sorted(d)
        sl_fn = lambda r: slope(Ds, [med(r[k]) for k in Ds])
        out['mtp_draft_ms_median'] = {k: round(med(d[k]), 3) for k in Ds}
        out['mtp_step_ms_slope'] = round(sl_fn(d), 3)
        allv = dict(d); allv['v1'] = v[1]
        out['rho_mtp'] = round(sl_fn(d) / med(v[1]), 4)
        out['rho_mtp_ci95'] = [round(x, 4) for x in boot(allv, lambda r: slope(Ds, [med(r[k]) for k in Ds]) / med(r['v1']))]
        out['rho_mtp_depth1'] = round(med(d[1]) / med(v[1]), 4)
        out['n_samples_per_depth'] = {k: len(d[k]) for k in Ds}
    out['lookup_ms_median'] = med(lu)
    out['rho_lu'] = round(med(lu) / med(v[1]), 7)
    out['rho_lu_ci95'] = [round(x, 7) for x in boot({'l': lu, 'v': v[1]}, lambda r: med(r['l']) / med(r['v']))]
    return out

if __name__ == '__main__':
    import os
    TR = '/workspace/strata-plus/traces'
    runs = {'qwen35-2b-mtp-q4_k_m': f'{TR}/raw/p4_2b_q4km.jsonl', 'qwen35-0.8b-mtp-q4_k_m': f'{TR}/raw/p4_08b_q4km.jsonl',
            'qwen35-0.8b-mtp-q8_0': f'{TR}/raw/p4_08b_q8.jsonl'}
    models = {k: analyse(p, 7) for k, p in runs.items() if os.path.exists(p)}
    cpu = subprocess.run("lscpu | grep -E 'Model name|^CPU\\(s\\)|Thread|L3'", shell=True, capture_output=True, text=True).stdout
    main = models['qwen35-2b-mtp-q4_k_m']
    doc = {'profile': 'P4', 'label': 'proxy CPU, modello denso, non AMD',
           'model': 'Qwen3.5-2B-MTP Q4_K_M (unsloth GGUF, llama.cpp d327bf1f + patch locale)',
           'hardware': cpu.strip(), 'threads': 6, 'flags': open(f'{TR}/raw/p4_cmd.txt').read().strip() if os.path.exists(f'{TR}/raw/p4_cmd.txt') else None,
           's': main['s'], 'rho_mtp': main['rho_mtp'], 'rho_lu': main['rho_lu'], 'step_ms': main['step_ms'],
           'n_samples': main['n_samples_per_T'][1],
           'source': 'timer in proxy/llama_spec_trace --mode p4 (llama_process+llama_synchronize; common_speculative_draft; SuffixDrafter::propose x1000), mediana, IC95 bootstrap',
           'note': 's(T): T righe di verifica a contesto = prompt (ctx_lens). rho_mtp in unita di step_ms per token di draft (pendenza). '
                   'rho_lu = propose(7) del SuffixDrafter Strata per round. Il costo degli expert MoE (H5) non e riproducibile su proxy denso.',
           'models': models}
    json.dump(doc, open(f'{TR}/cost_p4_cpu.json', 'w'), indent=1)
    print(json.dumps({k: {x: m[x] for x in ('s', 'rho_mtp', 'rho_mtp_ci95', 'rho_mtp_depth1', 'rho_lu', 'step_ms') if x in m} for k, m in models.items()}, indent=1))
