#!/usr/bin/env python3
"""Holdout v1.1 (proxy CPU, non AMD): 30 prompt per dominio (code/chat/edit), ID disgiunti dal set di tuning
(proxy_30 = i 30 del giro precedente, e quindi anche da agent_turns_bench/mtbench2 che usano gli stessi problemi).
Stesse fonti pinnate e stessi template di prepare_datasets.py; seed 20261026. Scrive datasets/holdout_90.jsonl
(campo split='holdout') e datasets/holdout_ids.json (seed, ID, sha256 sorgenti)."""
import json, os, random, hashlib
from prepare_datasets import REV, EDIT_TAG, MTBENCH_URL, get, hf_parquet
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datasets')
SEED, N = 20261026, 30
tune = {json.loads(l)['id'] for l in open(f'{D}/proxy_30.jsonl')}
for f in ('agent_turns_bench.jsonl', 'mtbench2.jsonl'):
    for l in open(f'{D}/{f}'):
        j = json.loads(l); tune.add(j['id'].split('#')[0])
rng = random.Random(SEED); meta = {'seed': SEED, 'n_per_domain': N, 'split': 'holdout', 'excluded_tune_ids': sorted(tune), 'sources': {}, 'ids': {}}
out = []
rows, sha = hf_parquet(*REV['humaneval'])
cand = [i for i, r in enumerate(rows) if r['task_id'] not in tune]
for i in sorted(rng.sample(cand, N)):
    out.append({'id': rows[i]['task_id'], 'category': 'code', 'source': 'humaneval', 'split': 'holdout',
                'prompt': 'Complete the following Python function. Reply with the full function in one code block.\n\n' + rows[i]['prompt']})
meta['sources']['humaneval'] = {'repo': REV['humaneval'][0], 'rev': REV['humaneval'][1], 'file_sha256': sha}
raw = get(MTBENCH_URL); mt = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
cand = [i for i, q in enumerate(mt) if f"mtbench-{q['question_id']}" not in tune]
for i in sorted(rng.sample(cand, N)):
    out.append({'id': f"mtbench-{mt[i]['question_id']}", 'category': 'chat', 'source': 'mt-bench', 'subcategory': mt[i]['category'],
                'split': 'holdout', 'prompt': mt[i]['turns'][0]})
meta['sources']['mt-bench'] = {'url': MTBENCH_URL, 'file_sha256': hashlib.sha256(raw).hexdigest()}
rows, sha = hf_parquet(*REV[EDIT_TAG])
def cid(i): r = rows[i]; return f"{EDIT_TAG}-{r.get('id', i)}-{r.get('name', '')}"
cand = [i for i in range(len(rows)) if cid(i) not in tune]
for i in sorted(rng.sample(cand, N)):
    r = rows[i]; instr = r.get('<campo istruzione>') or r.get('<campo istruzione breve>')
    out.append({'id': cid(i), 'category': 'edit', 'source': EDIT_TAG, 'split': 'holdout',
                'prompt': f"Edit the following Python code according to the instruction. Reply with the complete edited file in one code block.\n\nInstruction: {instr}\n\n```python\n{r['before']}\n```"})
meta['sources'][EDIT_TAG] = {'repo': REV[EDIT_TAG][0], 'rev': REV[EDIT_TAG][1], 'file_sha256': sha}
assert not ({o['id'] for o in out} & tune) and len({o['id'] for o in out}) == 3 * N
for c in ('code', 'chat', 'edit'): meta['ids'][c] = [o['id'] for o in out if o['category'] == c]
with open(f'{D}/holdout_90.jsonl', 'w') as f:
    for o in out: f.write(json.dumps(o, ensure_ascii=False) + '\n')
json.dump(meta, open(f'{D}/holdout_ids.json', 'w'), indent=1)
print({c: len(v) for c, v in meta['ids'].items()}, 'max chars', max(len(o['prompt']) for o in out))
