#!/usr/bin/env python3
"""check_v12 (proxy CPU, non AMD): 20 prompt per dominio (code/chat/edit), ID disgiunti da tune (proxy_30 + sessioni),
holdout_90 (mai riusato), diag_prompts e p4_prompts. Seed 20261027. Scrive datasets/check_v12.jsonl (split='check_v12')
e datasets/check_v12_ids.json. Derivato da prepare_holdout.py:
Holdout v1.1 (proxy CPU, non AMD): 30 prompt per dominio (code/chat/edit), ID disgiunti dal set di tuning
(proxy_30 = i 30 del giro precedente, e quindi anche da agent_turns_bench/mtbench2 che usano gli stessi problemi).
Stesse fonti pinnate e stessi template di prepare_datasets.py; seed 20261026. Scrive datasets/holdout_90.jsonl
(campo split='holdout') e datasets/holdout_ids.json (seed, ID, sha256 sorgenti)."""
import json, os, random, hashlib
from prepare_datasets import REV, EDIT_TAG, FIELD_INSTR, FIELD_INSTR_SHORT, MTBENCH_URL, get, hf_parquet
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datasets')
SEED, N = 20261027, 20
tune = {json.loads(l)['id'] for l in open(f'{D}/proxy_30.jsonl')}
for f in ('agent_turns_bench.jsonl', 'mtbench2.jsonl'):
    for l in open(f'{D}/{f}'):
        j = json.loads(l); tune.add(j['id'].split('#')[0])
for f in ('holdout_90.jsonl', 'diag_prompts.jsonl', 'p4_prompts.jsonl'):
    for l in open(f'{D}/{f}'):
        tune.add(json.loads(l)['id'].split('#')[0])
rng = random.Random(SEED); meta = {'seed': SEED, 'n_per_domain': N, 'split': 'check_v12', 'excluded_ids_tune_holdout90_diag_p4': sorted(tune), 'sources': {}, 'ids': {}}
out = []
rows, sha = hf_parquet(*REV['humaneval'])
cand = [i for i, r in enumerate(rows) if r['task_id'] not in tune]
for i in sorted(rng.sample(cand, N)):
    out.append({'id': rows[i]['task_id'], 'category': 'code', 'source': 'humaneval', 'split': 'check_v12',
                'prompt': 'Complete the following Python function. Reply with the full function in one code block.\n\n' + rows[i]['prompt']})
meta['sources']['humaneval'] = {'repo': REV['humaneval'][0], 'rev': REV['humaneval'][1], 'file_sha256': sha}
raw = get(MTBENCH_URL); mt = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
cand = [i for i, q in enumerate(mt) if f"mtbench-{q['question_id']}" not in tune]
for i in sorted(rng.sample(cand, N)):
    out.append({'id': f"mtbench-{mt[i]['question_id']}", 'category': 'chat', 'source': 'mt-bench', 'subcategory': mt[i]['category'],
                'split': 'check_v12', 'prompt': mt[i]['turns'][0]})
meta['sources']['mt-bench'] = {'url': MTBENCH_URL, 'file_sha256': hashlib.sha256(raw).hexdigest()}
rows, sha = hf_parquet(*REV[EDIT_TAG])
def cid(i): r = rows[i]; return f"{EDIT_TAG}-{r.get('id', i)}-{r.get('name', '')}"
cand = [i for i in range(len(rows)) if cid(i) not in tune]
for i in sorted(rng.sample(cand, N)):
    r = rows[i]; instr = r.get(FIELD_INSTR) or r.get(FIELD_INSTR_SHORT)
    out.append({'id': cid(i), 'category': 'edit', 'source': EDIT_TAG, 'split': 'check_v12',
                'prompt': f"Edit the following Python code according to the instruction. Reply with the complete edited file in one code block.\n\nInstruction: {instr}\n\n```python\n{r['before']}\n```"})
meta['sources'][EDIT_TAG] = {'repo': REV[EDIT_TAG][0], 'rev': REV[EDIT_TAG][1], 'file_sha256': sha}
assert not ({o['id'] for o in out} & tune) and len({o['id'] for o in out}) == 3 * N
for c in ('code', 'chat', 'edit'): meta['ids'][c] = [o['id'] for o in out if o['category'] == c]
with open(f'{D}/check_v12.jsonl', 'w') as f:
    for o in out: f.write(json.dumps(o, ensure_ascii=False) + '\n')
meta['licenses'] = {'humaneval': 'MIT', 'mt-bench': 'Apache-2.0 (repo FastChat)', EDIT_TAG: 'MIT'}
json.dump(meta, open(f'{D}/check_v12_ids.json', 'w'), indent=1)
print({c: len(v) for c, v in meta['ids'].items()}, 'max chars', max(len(o['prompt']) for o in out))
