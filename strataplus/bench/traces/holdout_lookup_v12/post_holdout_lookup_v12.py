#!/usr/bin/env python3
"""proxy CPU, non AMD. holdout_lookup_v12: raw/holdout_lookup_v12/*.jsonl -> traces/holdout_lookup_v12/ (file nuovi).
Header + per request: split, spec_params (drafter, n_max=dmax, n_min, p_min, min/max match), licenza, greedy_equal_ref, first_divergence_pos.
AL_full = mean(accepted+1) su tutti i round; AL_pre_div = idem sui round con pos+committed <= first_divergence_pos (tutti se identico),
stessa definizione di tools/check_v12_divergence.py. Ref = output_ids di holdout_tf_d7 (T=1 greedy, stesso build LLAMAFILE ON).
Misura descrittiva: nessun parametro scelto o tarato su questi dati."""
import json, hashlib, collections, time, os, sys
RAW = '/workspace/strata-plus/traces/raw/holdout_lookup_v12'; OUT = '/workspace/strata-plus/traces/holdout_lookup_v12'
os.makedirs(OUT, exist_ok=True)
NOTE = 'misura descrittiva su holdout v1.1: nessun parametro scelto o tarato su questi dati'
LIC = {'humaneval': ('MIT', 'HF openai/openai_humaneval @ 7dce6050a7d6d172f3cc5c32aa97f52fa1a2e544'),
       'mt-bench': ('Apache-2.0 (repo FastChat)', 'lm-sys/FastChat @ 587d5cfa1609a43d192cedb8441cac3c17db105d fastchat/llm_judge/data/mt_bench/question.jsonl'),
       'edit_np': ('MIT', 'HF edit_np @<revisione non pubblicata>')}
src = {json.loads(l)['id']: json.loads(l)['source'] for l in open('/workspace/strata-bench/datasets/holdout_90.jsonl')}
ref = {}
for l in open(f'{RAW}/ref_holdout_tf.tsv'):
    k, v = l.rstrip('\n').split('\t'); ref[k] = [int(x) for x in v.split(',') if x]
def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y: break
        n += 1
    return n
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
summary = {'label': 'proxy CPU, non AMD', 'note': NOTE, 'created': time.strftime('%F %T %Z'), 'doc': __doc__,
           'ref_file': '/workspace/strata-plus/traces/raw/v11_holdout/holdout_tf_d7.jsonl', 'ref_sha256': sha('/workspace/strata-plus/traces/raw/v11_holdout/holdout_tf_d7.jsonl'),
           'build': 'proxy/llama_spec_trace.v11.bin (libggml-cpu build/, GGML_LLAMAFILE ON)', 'arms': {}}
for n in map(int, sys.argv[1:] or ['7', '12', '16']):
    run = f'holdout_lookup_v12_n{n}'; rows = [json.loads(l) for l in open(f'{RAW}/{run}.jsonl')]
    rounds = collections.defaultdict(list); ends = {}
    for j in rows:
        if j['type'] == 'round': rounds[j['req_id']].append(j)
        elif j['type'] == 'request_end': ends[j['req_id']] = j
    sp = {'drafter': 'strata::spec::SuffixDrafter(min_match=3,max_match=64)::propose(max_k=dmax)', 'lookup_min_match': 3, 'lookup_max_match': 64,
          'draft_n_max': n, 'draft_n_max_impl': n, 'draft_n_min': 0, 'draft_p_min': 0.0,
          'draft_p_min_note': 'non usato in lookup-only (nessuna probabilita\' nel draft lookup)',
          'code_refs': 'proxy/llama_spec_trace.cpp:175 (SuffixDrafter(3,64)), :177 lbuf(dmax), :293 propose(dmax), :328-331 draft=min(lk, token rimasti); suffix_drafter.cpp:18-19,84; n_rs_seq=max(--spec-draft-n-max 3, dmax) (llama_spec_trace.cpp:113, common.h:401-406, llama-memory-recurrent.cpp:214)',
          'llamacpp_ngram_caps_apply': False, 'per_round_cap': f'min(len suffisso, token rimasti), suffisso fino a dmax={n}'}
    of = f'{OUT}/{run}.jsonl'; agg = collections.defaultdict(lambda: {'full': [0, 0], 'pre': [0, 0], 'n': 0, 'eq': 0}); per = []
    with open(of, 'w') as o:
        o.write(json.dumps({'type': 'header', 'schema': 'strataplus.v1.1', 'label': 'proxy CPU, non AMD', 'split': 'holdout_lookup_v12', 'run_id': run,
                            'note': NOTE, 'spec_params': sp, 'ref_source': 'holdout_tf_d7 output_ids (own T=1 greedy)'}) + '\n')
        for j in rows:
            if j['type'] == 'request':
                k = j['req_id']; y = ref[k]; out = ends[k]['output_ids']; d = lcp(out, y); dv = None if d == len(out) == len(y) else d
                lic, up = LIC[src[k]]
                lim = dv if dv is not None else 10**9; rs = rounds[k]
                full = [r['accepted'] + 1 for r in rs]; pre = [r['accepted'] + 1 for r in rs if r['pos'] + r['committed'] <= lim]
                j = {**j, 'split': 'holdout_lookup_v12', 'spec_params': sp, 'license': lic, 'upstream': up, 'note': NOTE,
                     'greedy_equal_ref': dv is None, 'first_divergence_pos': dv}
                g = agg[j['domain']]; a = agg['ALL']
                for G in (g, a):
                    G['full'][0] += sum(full); G['full'][1] += len(full); G['pre'][0] += sum(pre); G['pre'][1] += len(pre); G['n'] += 1; G['eq'] += dv is None
                per.append({'req_id': k, 'domain': j['domain'], 'greedy_equal_ref': dv is None, 'first_divergence_pos': dv,
                            'AL_full': round(sum(full) / len(full), 4), 'AL_pre_div': round(sum(pre) / len(pre), 4) if pre else None, 'rounds_full': len(full), 'rounds_pre_div': len(pre)})
            o.write(json.dumps(j) + '\n')
    summ = {g: {'requests': v['n'], 'greedy_equal_ref': v['eq'], 'AL_full': round(v['full'][0] / v['full'][1], 4), 'rounds_full': v['full'][1],
                'AL_pre_div': round(v['pre'][0] / v['pre'][1], 4), 'rounds_pre_div': v['pre'][1]} for g, v in sorted(agg.items())}
    summary['arms'][run] = {'n_max': n, 'raw_file': f'{RAW}/{run}.jsonl', 'raw_sha256': sha(f'{RAW}/{run}.jsonl'), 'file': of, 'sha256': sha(of),
                            'summary': summ, 'first_divergence_pos': {p['req_id']: p['first_divergence_pos'] for p in per if p['first_divergence_pos'] is not None}, 'per_request': per}
    print(run, json.dumps(summ))
json.dump(summary, open(f'{OUT}/holdout_lookup_v12_summary.json', 'w'), indent=1)
