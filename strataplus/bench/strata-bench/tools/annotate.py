#!/usr/bin/env python3
"""proxy CPU, non numeri AMD.
Converte le uscite grezze di proxy/llama_spec_trace (traces/raw/*.jsonl) nel formato strataplus.v1 di
/workspace/strata-plus/log_format.md: riga request per prima (con data_kind, dmax, ref_tokens, sha256), poi le righe
round con pos = token di output gia' committati (D4), committed = accepted+1, acc.{mtp,lookup} controfattuali vs y,
cost_est col profilo P4 misurato (cost_p4_cpu.json), ms_split/ms_measured dai timer.
y (ref_tokens) = output del run baseline base_r0 (greedy, nessuna speculazione)."""
import glob, hashlib, json, os, sys

TR = '/workspace/strata-plus/traces'
RAW = f'{TR}/raw'
MODEL = 'Qwen3.5-2B-MTP Q4_K_M (unsloth/Qwen3.5-2B-MTP-GGUF@e05864f8, Qwen3.5-2B-Q4_K_M.gguf)'
ENGINE_REV = 'd327bf1f0780f87b8c01b367b61853b0c291d7c4+patches/llamacpp-draft-mtp-probs.patch'

def sha(ids): return hashlib.sha256(','.join(map(str, ids)).encode()).hexdigest()
def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y: break
        n += 1
    return n

def load(path):
    reqs, rounds = [], {}
    for l in open(path):
        try: j = json.loads(l)
        except json.JSONDecodeError: continue   # a run still being written
        if j['type'] == 'request': reqs.append(j)
        elif j['type'] == 'round': rounds.setdefault((j['req_id'], j['rep']), []).append(j)
    return reqs, rounds

def main():
    p4 = json.load(open(f'{TR}/cost_p4_cpu.json')) if os.path.exists(f'{TR}/cost_p4_cpu.json') else None
    prof = None
    if p4:
        prof = p4['models']['qwen35-2b-mtp-q4_k_m']
    ref_reqs, _ = load(f'{RAW}/base_r0.jsonl')
    y = {r['req_id']: r['output_ids'] for r in ref_reqs}
    meta = {r['req_id']: r for r in ref_reqs}
    ds = {}
    for l in open('/workspace/strata-bench/datasets/proxy_30.jsonl'):
        j = json.loads(l); ds[j['id']] = j
    report = {}
    for f in sorted(glob.glob(f'{RAW}/*.jsonl')):
        run = os.path.basename(f)[:-6]
        if run == 'campaign' or run.startswith('p4') or run.startswith('diag_'): continue
        reqs, rounds = load(f)
        out = open(f'{TR}/{run}.jsonl', 'w')
        neq = 0
        for rq in reqs:
            rid = rq['req_id']; yr = y.get(rid)
            mode = 'teacher_forced' if run.startswith('tf_') else 'live'
            rr = rounds.get((rid, rq['rep']), [])
            dm = max((len(x['cand']['mtp']['tokens']) for x in rr), default=0)
            row = {'type': 'request', 'schema': 'strataplus.v1', 'label': 'proxy CPU', 'run_id': run, 'engine': 'llamacpp',
                   'engine_rev': ENGINE_REV, 'model': MODEL, 'flags': rq['flags'] + ' (greedy, temp 0)',
                   'dataset': ds[rid]['source'] if rid in ds else rq['dataset'], 'domain': rq['domain'], 'req_id': rid,
                   'session_id': None, 'turn': 0, 'prompt_sha256': sha(rq['prompt_ids']), 'prompt_tokens': rq['prompt_tokens'],
                   'output_sha256': sha(rq['output_ids']), 'output_tokens': rq['output_tokens'],
                   'ref_output_sha256': sha(yr) if yr is not None else None, 'data_kind': mode,
                   'dmax': dm if dm else None, 'ref_tokens': yr, 'prompt_ids': rq['prompt_ids'],
                   'greedy_equal_ref': (rq['output_ids'] == yr), 'rep': rq['rep'],
                   'stats': {k: rq[k] for k in ('verify_rounds', 'drafted', 'accepted', 'prefill_ms', 'decode_ms', 'draft_ms', 'verify_ms', 'mtp_process_ms')}}
            oo = rq['output_ids']
            div = next((i for i, (u, v) in enumerate(zip(oo, yr or [])) if u != v), None)
            if div is None and yr is not None and len(oo) != len(yr): div = min(len(oo), len(yr))
            row['first_divergence_pos'] = div   # first output index where this run differs from y (None = identical)
            row['acc_ref'] = 'self_output'      # acc = LCP with this run's own committed output (= y when greedy_equal_ref)
            neq += row['greedy_equal_ref']
            out.write(json.dumps(row) + '\n')
            P = rq['prompt_tokens']
            for x in rr:
                pos = x['gen_index']; ctx = P + pos
                mt = x['cand']['mtp']['tokens']; lt = x['cand']['lookup']['tokens']
                T = x['T']
                d_mtp = len(mt)
                cost = None
                if prof:
                    s = prof['s']
                    cv = s[T - 1] if T - 1 < len(s) else None
                    cost = {'profile': 'P4-cpu-2b', 'c_verify': cv, 'c_mtp': prof['rho_mtp'], 'c_lookup': prof['rho_lu'],
                            'd_mtp': d_mtp, 'total': (cv + prof['rho_mtp'] * d_mtp + prof['rho_lu']) if cv is not None else None}
                ms = x['ms_measured']
                o = {'type': 'round', 'schema': 'strataplus.v1', 'label': 'proxy CPU', 'run_id': run, 'req_id': rid, 'r': x['r'],
                     'pos': pos, 'kv_pos': x['pos'], 'ctx_len': ctx, 'ctx_bucket': 0 if ctx < 6000 else 1 if ctx < 24000 else 2,
                     'source': x['source'], 'k_proposed': x['k_proposed'], 'T': T, 'proposal': x['proposal'],
                     'cand': {'mtp': ({'tokens': mt, 'probs': x['cand']['mtp']['probs']} if d_mtp else None),
                              'lookup': ({'tokens': lt, 'match': x['cand']['lookup']['match']} if lt else None)},
                     'accepted': x['accepted'], 'committed': x['accepted'] + 1,
                     'ms_measured': round(ms['draft'] + ms['lookup'] + ms['verify'] + ms['mtp_process'], 4),
                     'ms_split': {'verify': ms['verify'], 'mtp': round(ms['draft'] + ms['mtp_process'], 4), 'mtp_draft': ms['draft'],
                                  'mtp_process': ms['mtp_process'], 'lookup': ms['lookup'], 'commit': None},
                     'cost_est': cost, 'policy': x['policy'] + '@d327bf1f', 'policy_note': '', 'domain': x['domain'],
                     'target_tokens': x['target_tokens']}
                # counterfactual acceptance vs the target greedy continuation of THIS path (own output); identical to
                # LCP with y up to first_divergence_pos, the only definition that stays valid after a divergence
                o['acc'] = {'mtp': lcp(mt, oo[pos:]) if d_mtp else None, 'lookup': lcp(lt, oo[pos:]) if lt else 0}
                o['censored'] = {'mtp': False, 'lookup': False}
                o['after_divergence'] = (div is not None and pos >= div)
                out.write(json.dumps(o) + '\n')
        out.close()
        report[run] = {'requests': len(reqs), 'greedy_equal_ref': neq}
    json.dump(report, open(f'{TR}/annotate_report.json', 'w'), indent=1)
    print(json.dumps(report, indent=1))

if __name__ == '__main__':
    main()
