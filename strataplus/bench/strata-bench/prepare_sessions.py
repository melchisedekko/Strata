#!/usr/bin/env python3
"""Sessioni multi-turno (proxy CPU, non AMD).
agent_turns_bench: sessioni di edit reali a 3 turni sullo stesso file (dataset di edit con licenza non pubblicabile edit_np, stessi 10 problemi del suo file jsonl):
  t0 = edit con <campo istruzione breve>, t1 = feedback 'test suite' con i test reali del problema, t2 = docstring+type hint
  sulle stesse funzioni. mtbench2: MT-Bench a 2 turni nativi (stessi 10 question_id di mtbench.jsonl)."""
import io, json, hashlib, urllib.request, os
from prepare_datasets import REV, EDIT_TAG  # valori locali, vedi _private() in prepare_datasets.py
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")
EDIT_URL = "https://huggingface.co/datasets/{}/resolve/{}/{}".format(*REV[EDIT_TAG])
MTB = ("https://raw.githubusercontent.com/lm-sys/FastChat/587d5cfa1609a43d192cedb8441cac3c17db105d/"
       "fastchat/llm_judge/data/mt_bench/question.jsonl")
def get(u):
    with urllib.request.urlopen(u, timeout=120) as r: return r.read()
import pyarrow.parquet as pq
raw = get(EDIT_URL); rows = pq.read_table(io.BytesIO(raw)).to_pylist(); sha_edit = hashlib.sha256(raw).hexdigest()
want = [json.loads(l)["id"] for l in open(f"{D}/{EDIT_TAG}.jsonl")]
byid = {f"{EDIT_TAG}-{r.get('id')}-{r.get('name','')}": r for r in rows}
out = []
for wid in want:
    r = byid[wid]; sid = "agent-" + wid
    t = [
      ("Edit the following Python code according to the instruction. Reply with the complete edited file in one code block.\n\n"
       f"Instruction: {r['<campo istruzione breve>']}\n\n```python\n{r['before']}\n```"),
      ("I ran the test suite against your edited file. These are the tests:\n\n```python\n" + r["tests"] + "\n```\n\n"
       "Make sure the code passes all of them and fix anything that would fail. Reply with the complete file in one code block."),
      ("Now add a docstring and type hints to every function and method you changed, without changing behaviour. "
       "Reply with the complete file in one code block."),
    ]
    for i, txt in enumerate(t):
        out.append({"id": f"{sid}#t{i}", "category": "agent_edit", "source": EDIT_TAG, "session_id": sid, "turn": str(i), "prompt": txt})
raw2 = get(MTB); mt = {q["question_id"]: q for q in map(json.loads, raw2.decode().splitlines())}
mout = []
for l in open(f"{D}/mtbench.jsonl"):
    q = mt[int(json.loads(l)["id"].split("-")[1])]; sid = f"mtbench2-{q['question_id']}"
    for i, txt in enumerate(q["turns"][:2]):
        mout.append({"id": f"{sid}#t{i}", "category": "chat", "source": "mt-bench", "session_id": sid, "turn": str(i), "prompt": txt})
for name, items in (("agent_turns_bench", out), ("mtbench2", mout)):
    with open(f"{D}/{name}.jsonl", "w") as f:
        for it in items: f.write(json.dumps(it, ensure_ascii=False) + "\n")
with open(f"{D}/sessions_meta.json", "w") as f:
    json.dump({EDIT_TAG: {"url": EDIT_URL, "sha256": sha_edit, "fields": ["<campo istruzione breve>", "before", "tests"]},
               "mt-bench": {"url": MTB, "sha256": hashlib.sha256(raw2).hexdigest()},
               "agent_turns_bench": len(out), "mtbench2": len(mout)}, f, indent=1)
print(len(out), len(mout))
