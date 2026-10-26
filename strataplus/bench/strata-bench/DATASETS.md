# DATASETS — sottoinsiemi fissi per Strata+ (proxy CPU e, più avanti, AMD)

Generati da `prepare_datasets.py` (seed **20261025**, 10 ID per dominio, campionamento senza reinserimento con
`random.Random(seed)`; Spec-Bench: 2 per categoria). Lista ID e sha256 dei file sorgente in `datasets/subset_ids.json`.
Formato JSONL comune: `{"id","category","source","prompt"}`; `category` = dominio (`code|chat|edit`, `specbench:<cat>`).

| Dominio | Dataset | Fonte (versione esatta) | Licenza | Righe sorgente | Uso |
|---|---|---|---|---|---|
| code | HumanEval | HF `openai/openai_humaneval` @ `7dce6050a7d6d172f3cc5c32aa97f52fa1a2e544` (parquet sha256 `2f2871a1…dfcfb6`) | MIT | 164 | prompt = "Complete the following Python function…" + firma/docstring |
| chat | MT-Bench (solo 1° turno) | `lm-sys/FastChat` @ `587d5cfa1609a43d192cedb8441cac3c17db105d`, `fastchat/llm_judge/data/mt_bench/question.jsonl` | Apache-2.0 (repo FastChat) | 80 | primo turno; la sottocategoria resta in `source`/id |
| edit | dataset di edit con licenza non pubblicabile (`edit_np`) | HF, revisione `<revisione non pubblicata>` (sha256 `<sha256 non pubblicato>`) | MIT | n.p. | istruzione + codice originale, prompt "Edit the following Python code…" |
| (extra) | Spec-Bench | `hemingkx/Spec-Bench` @ `fd2c1cd7d2201ef71db4c5f4e455008f017967bf`, `data/spec_bench/question.jsonl` | Apache-2.0 | 480 | 2 per categoria (13 cat.), per la fase AMD; non usato nelle tracce CPU |

File: `datasets/humaneval.jsonl`, `mtbench.jsonl`, `edit_np.jsonl`, `specbench.jsonl`; `datasets/proxy_30.jsonl` =
humaneval+mtbench+edit_np (30 prompt, l'insieme usato per le tracce); `datasets/p4_prompts.jsonl` = primi 2 per
dominio di proxy_30 (profilo di costo P4).

Template di chat usato nel proxy llama.cpp (Qwen3.5, thinking disattivato):
`<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n` (in `proxy/llama_spec_trace.cpp`).
