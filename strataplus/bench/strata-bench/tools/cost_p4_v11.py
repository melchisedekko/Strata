#!/usr/bin/env python3
"""proxy CPU, modello denso, non AMD. P4 v1.1 (indicizzato per (T, d)). Mediane dei campioni di
llama_spec_trace.v11.bin --mode p4: verify(T) = llama_process di T righe + sync; mtp_draft(d) = common_speculative_draft
a profondita' d (d passi della testa MTP, sampler backend top_k=10, nessun calcolo di prob piene); mtp_process(T) =
common_speculative_process sulle T righe verificate. cost(T,d) = [verify(T) + mtp_draft(d) + (mtp_process(T) se d>0)] / verify(1).
IC95 bootstrap (2000, seed 20261025)."""
import json, os, random, statistics as st, subprocess
from cost_p4 import boot, slope
TR = '/workspace/strata-plus/traces'; RAW = f'{TR}/raw/v11'
med = st.median
def analyse(path):
    v, pr, d, lu, ctx = {}, {}, {}, [], set()
    for l in open(path):
        j = json.loads(l); ctx.add(j['ctx_len'])
        if j['what'] == 'verify': v.setdefault(j['T'], []).append(j['ms']); pr.setdefault(j['T'], []).append(j['mtp_process_ms'])
        elif j['what'] == 'mtp_draft': d.setdefault(j['depth'], []).append(j['ms'])
        elif j['what'] == 'lookup': lu.append(j['ms'])
    d[0] = [0.0]
    step = med(v[1]); Ts = sorted(v); Ds = sorted(d)
    s = [med(v[T]) / step for T in Ts]
    cost = {}; ci = {}
    for T in Ts:
        for dd in Ds:
            f = lambda r, T=T, dd=dd: (med(r['v']) + med(r['d']) + (med(r['p']) if dd > 0 else 0)) / med(r['v1'])
            samp = {'v': v[T], 'd': d[dd], 'p': pr[T], 'v1': v[1]}
            cost[f'{T},{dd}'] = round(f(samp), 4); ci[f'{T},{dd}'] = [round(x, 4) for x in boot(samp, f, B=500)]
    Dpos = [x for x in Ds if x > 0]
    out = {'T': Ts, 's': [round(x, 4) for x in s],
           's_ci95': [[round(a, 4), round(b, 4)] for a, b in (boot({1: v[1], T: v[T]}, lambda r, T=T: med(r[T]) / med(r[1])) for T in Ts)],
           'step_ms': round(step, 3), 'verify_ms_median': {T: round(med(v[T]), 3) for T in Ts},
           'mtp_process_ms_median': {T: round(med(pr[T]), 3) for T in Ts},
           'mtp_draft_ms_median': {x: round(med(d[x]), 3) for x in Dpos},
           'rho_mtp': round(slope(Dpos, [med(d[x]) for x in Dpos]) / step, 4),
           'rho_mtp_depth1': round(med(d[1]) / step, 4),
           'rho_lu': round(med(lu) / step, 7), 'lookup_ms_median': med(lu),
           'cost_T_d': cost, 'cost_T_d_ci95_B500': ci,
           'cost_by_k': {'mtp': {k: cost[f'{k+1},{k}'] for k in range(1, min(max(Ts) - 1, max(Ds)) + 1)},
                         'lookup': {k: round(cost[f'{k+1},0'] + med(lu) / step, 4) for k in range(1, max(Ts))}},
           'n_samples_per_T': {T: len(v[T]) for T in Ts}, 'n_samples_per_depth': {x: len(d[x]) for x in Dpos}, 'ctx_lens': sorted(ctx)}
    return out
if __name__ == '__main__':
    runs = json.loads(os.environ['COST_RUNS']) if os.environ.get('COST_RUNS') else {'qwen35-2b-mtp-q4_k_m': f'{RAW}/p4_2b_q4km.jsonl', 'qwen35-2b-mtp-q8_0': f'{RAW}/p4_2b_q8.jsonl'}
    models = {k: analyse(p) for k, p in runs.items() if os.path.exists(p)}
    cpu = subprocess.run("lscpu | grep -E 'Model name|^CPU\\(s\\)|Thread|L3'", shell=True, capture_output=True, text=True).stdout
    m = models['qwen35-2b-mtp-q4_k_m']
    old = os.environ.get('COST_OUT', f'{TR}/cost_p4_cpu.json')
    if os.path.exists(old): raise SystemExit(f'REFUSED: {old} esiste (file annunciato con sha256 = immutabile)')
    if os.path.exists(old) and json.load(open(old)).get('schema_version') != 'p4.v1.1': os.replace(old, f'{TR}/cost_p4_cpu.v1_prev_round.json')
    doc = {'schema_version': 'p4.v1.1', 'profile': 'P4-cpu-2b-q4km', 'label': 'proxy CPU, modello denso, non AMD',
           'model': 'Qwen3.5-2B-MTP Q4_K_M (unsloth GGUF @e05864f8, llama.cpp d327bf1f + patch locale)',
           'hardware': cpu.strip(), 'threads': 6, 'flags': open(f'{RAW}/p4_cmd.txt').read().strip(),
           's': m['s'], 'rho_mtp': m['rho_mtp'], 'rho_lu': m['rho_lu'], 'step_ms': m['step_ms'], 'n_samples': m['n_samples_per_T'][1],
           'cost_T_d': m['cost_T_d'], 'cost_by_k': m['cost_by_k'],
           'cost_def': 'cost(T,d) = [verify(T) + mtp_draft(d) + (mtp_process(T) se d>0)] / verify(1); round MTP a k: (T=k+1, d=k); '
                       'round lookup a k: (T=k+1, d=0) + rho_lu; tutte mediane, unita = step_ms (verify T=1)',
           'source': 'timer in proxy/llama_spec_trace.v11.bin --mode p4; ps prima/durante in raw/v11/p4_ps.log',
           'note': 'Solo rapporti relativi; tempi CPU di modello denso. Costo expert MoE (H5) non riproducibile.',
           'models': models}
    json.dump(doc, open(old, 'w'), indent=1)
    print(json.dumps({k: {x: mm[x] for x in ('s', 'rho_mtp', 'rho_mtp_depth1', 'rho_lu', 'step_ms', 'cost_by_k')} for k, mm in models.items()}, indent=1))
