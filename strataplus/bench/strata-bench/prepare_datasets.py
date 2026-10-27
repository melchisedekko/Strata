#!/usr/bin/env python3
"""Scarica e prepara sottoinsiemi FISSI (seed + lista ID salvata) dei dataset del protocollo Strata+.

Output: datasets/<nome>.jsonl con campi: id, category (code|chat|edit|specbench:<cat>), source, prompt (testo utente),
system (opzionale). Più datasets/subset_ids.json con seed, revisioni pinnate e ID scelti.
Le revisioni sono pinnate: cambiare una revisione = nuovo protocollo.
"""
import argparse, io, json, os, random, sys, urllib.request, hashlib


def _private(key):
    """Valore SOLO LOCALE (mai pubblicato) del dataset di edit con licenza non pubblicabile (etichetta pubblica: edit_np).
    Ordine: variabile d'ambiente `key`; altrimenti il file locale STRATAPLUS_PRIVATE_ENV
    (default /workspace/lic_rm/edit_dataset.env, righe KEY=VALORE). Se manca: errore esplicito."""
    v = os.environ.get(key, "").strip()
    path = os.environ.get("STRATAPLUS_PRIVATE_ENV", "/workspace/lic_rm/edit_dataset.env")
    if not v and os.path.isfile(path):
        for line in open(path):
            k, _, x = line.strip().partition("=")
            if k == key:
                v = x.strip()
    if not v:
        sys.exit(f"ERRORE: {key} non impostata (ne' in ambiente ne' in {path}). "
                 "Impostala o crea il file locale: vedi /workspace/lic_rm/README_edit_dataset.md")
    return v


# Etichetta locale (prefisso ID, campo source, nome file) del dataset di edit con licenza non pubblicabile.
EDIT_TAG = _private("STRATAPLUS_EDIT_TAG")
# nomi dei campi istruzione (completa / breve) del dataset: valori solo locali
FIELD_INSTR = _private("STRATAPLUS_EDIT_FIELD_INSTR")
FIELD_INSTR_SHORT = _private("STRATAPLUS_EDIT_FIELD_INSTR_SHORT")

REV = {
    "humaneval": ("openai/openai_humaneval", "7dce6050a7d6d172f3cc5c32aa97f52fa1a2e544",
                  "openai_humaneval/test-00000-of-00001.parquet"),
    EDIT_TAG: (_private("STRATAPLUS_EDIT_DATASET"), _private("STRATAPLUS_EDIT_DATASET_REV"), "data/test-00000-of-00001.parquet"),
}
MTBENCH_URL = ("https://raw.githubusercontent.com/lm-sys/FastChat/587d5cfa1609a43d192cedb8441cac3c17db105d/"
               "fastchat/llm_judge/data/mt_bench/question.jsonl")
SPECBENCH_URL = ("https://raw.githubusercontent.com/hemingkx/Spec-Bench/fd2c1cd7d2201ef71db4c5f4e455008f017967bf/"
                 "data/spec_bench/question.jsonl")


def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def hf_parquet(repo, rev, path):
    import pyarrow.parquet as pq
    raw = get(f"https://huggingface.co/datasets/{repo}/resolve/{rev}/{path}")
    return pq.read_table(io.BytesIO(raw)).to_pylist(), hashlib.sha256(raw).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets"))
    ap.add_argument("--seed", type=int, default=20261025)
    ap.add_argument("--n", type=int, default=10, help="prompt per dominio")
    ap.add_argument("--n-specbench", type=int, default=2, help="prompt per categoria SpecBench")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = random.Random(a.seed)
    meta = {"seed": a.seed, "n": a.n, "sources": {}, "ids": {}}

    rows, sha = hf_parquet(*REV["humaneval"])
    pick = sorted(rng.sample(range(len(rows)), a.n))
    he = [{"id": rows[i]["task_id"], "category": "code", "source": "humaneval",
           "prompt": "Complete the following Python function. Reply with the full function in one code block.\n\n"
                     + rows[i]["prompt"]} for i in pick]
    meta["sources"]["humaneval"] = {"repo": REV["humaneval"][0], "rev": REV["humaneval"][1], "file_sha256": sha,
                                    "license": "MIT", "rows": len(rows)}

    mt = [json.loads(l) for l in get(MTBENCH_URL).decode().splitlines() if l.strip()]
    pick = sorted(rng.sample(range(len(mt)), a.n))
    mtb = [{"id": f"mtbench-{mt[i]['question_id']}", "category": "chat", "source": "mt-bench",
            "subcategory": mt[i]["category"], "prompt": mt[i]["turns"][0]} for i in pick]   # solo primo turno
    meta["sources"]["mt-bench"] = {"url": MTBENCH_URL, "license": "Apache-2.0 (FastChat)", "rows": len(mt)}

    rows, sha = hf_parquet(*REV[EDIT_TAG])
    pick = sorted(rng.sample(range(len(rows)), a.n))
    ed = []
    for i in pick:
        r = rows[i]
        instr = r.get(FIELD_INSTR) or r.get(FIELD_INSTR_SHORT)
        ed.append({"id": f"{EDIT_TAG}-{r.get('id', i)}-{r.get('name', '')}", "category": "edit", "source": EDIT_TAG,
                   "prompt": f"Edit the following Python code according to the instruction. Reply with the complete "
                             f"edited file in one code block.\n\nInstruction: {instr}\n\n```python\n{r['before']}\n```"})
    meta["sources"][EDIT_TAG] = {"repo": REV[EDIT_TAG][0], "rev": REV[EDIT_TAG][1], "file_sha256": sha,
                                    "license": "MIT", "rows": len(rows), "instruction": FIELD_INSTR}

    sb = [json.loads(l) for l in get(SPECBENCH_URL).decode().splitlines() if l.strip()]
    bycat = {}
    for q in sb:
        bycat.setdefault(q["category"], []).append(q)
    spb = []
    for cat in sorted(bycat):
        for q in rng.sample(bycat[cat], min(a.n_specbench, len(bycat[cat]))):
            spb.append({"id": f"specbench-{q['question_id']}", "category": f"specbench:{cat}", "source": "spec-bench",
                        "prompt": q["turns"][0]})
    meta["sources"]["spec-bench"] = {"url": SPECBENCH_URL, "license": "Apache-2.0", "rows": len(sb)}

    for name, items in (("humaneval", he), ("mtbench", mtb), (EDIT_TAG, ed), ("specbench", spb)):
        with open(os.path.join(a.out, f"{name}.jsonl"), "w") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        meta["ids"][name] = [it["id"] for it in items]
    with open(os.path.join(a.out, "subset_ids.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(json.dumps({k: len(v) for k, v in meta["ids"].items()}))


if __name__ == "__main__":
    main()
