#!/usr/bin/env python3
"""proxy CPU, non AMD. agent_v12 (binario v12 invariato per i 4 modi): clamp in post-processing di committed/accepted al primo EOS /
fine output (errata holdout_lookup_v12: il tracer v12 scrive committed=ids.size() anche oltre l'EOG, llama_spec_trace_v12.cpp:401 vs :431).
Regola per ogni riga round: committed_c = min(committed, output_tokens - pos); accepted_c = min(accepted, committed_c).
Se cambia: committed_raw/accepted_raw conservati, eos_clamped=true. Conteggio committed_clamped_at_eos in header e request."""
import json, sys, glob
V = sys.argv[1]
RULE = 'committed = min(committed_raw, output_tokens - pos); accepted = min(accepted_raw, committed); AL di round = min(accepted+1, committed)'
tot = {}
for f in sorted(glob.glob(f'{V}/agent_v12_*.jsonl')):
    rows = [json.loads(l) for l in open(f)]
    L = {(j['req_id'], j.get('rep', 0)): j['output_tokens'] for j in rows if j['type'] == 'request'}
    n = {}
    for j in rows:
        if j['type'] == 'round' and j.get('committed', 0) > 0:
            k = (j['req_id'], j.get('rep', 0)); c = min(j['committed'], L[k] - j['pos'])
            if c < j['committed']:
                j['committed_raw'], j['accepted_raw'] = j['committed'], j['accepted']
                j['committed'] = c; j['accepted'] = min(j['accepted'], c); j['eos_clamped'] = True; n[k] = n.get(k, 0) + 1
    for j in rows:
        if j['type'] == 'header': j['eos_clamp'] = {'rule': RULE, 'committed_clamped_at_eos': sum(n.values()), 'tracer': 'llama_spec_trace.v12.nollamafile (non corretto, clamp solo in post)'}
        if j['type'] == 'request': j['committed_clamped_at_eos'] = n.get((j['req_id'], j.get('rep', 0)), 0)
    open(f, 'w').write('\n'.join(json.dumps(j, ensure_ascii=False) for j in rows) + '\n')
    tot[f.split('/')[-1]] = {'committed_clamped_at_eos': sum(n.values()), 'requests': [k[0] for k in n]}
print(json.dumps(tot))
