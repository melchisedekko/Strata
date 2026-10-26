#!/usr/bin/env python3
"""proxy CPU, non AMD. Validazione strutturale tracce agent_v12 prima del manifest (nessuna metrica): header + spec_params, license, truncation in ogni request;
TF Dmax=7: per ogni round cand.mtp con 7 token e probs/probs_sampler/ent della stessa lunghezza, vmargin con T righe (p_top1 per step)."""
import json, sys, glob, os, collections
D = sys.argv[1]; bad = []; rep = {}
for f in sorted(glob.glob(f'{D}/agent_v12_*.jsonl')):
    b = os.path.basename(f); c = collections.Counter(); first = None
    for i, l in enumerate(open(f)):
        j = json.loads(l); c[j['type']] += 1
        if i == 0: first = j['type']
        if j['type'] == 'request' and not all(x in j for x in ('spec_params', 'license', 'truncation')): bad.append(f'{b}: request senza spec_params {j["req_id"]}')
        if j['type'] == 'round':
            if len(j['vmargin']) != j['T']: bad.append(f'{b}: vmargin {len(j["vmargin"])} != T {j["T"]} pos {j["pos"]}')
            if j['split'] != 'agent_v12': bad.append(f'{b}: split {j["split"]}')
            if b.startswith('agent_v12_tf_d7'):
                m = j['cand']['mtp']
                if not m or len(m['tokens']) != 7 or not (len(m['probs']) == len(m['probs_sampler']) == len(m['ent']) == 7):
                    c['tf_rounds_bad_mtp'] += 1
    if first != 'header': bad.append(f'{b}: prima riga {first} (atteso header)')
    rep[b] = dict(c)
print(json.dumps(rep)); print('\n'.join(bad[:20]))
if bad or any(v.get('tf_rounds_bad_mtp') for v in rep.values()): sys.exit(1)
