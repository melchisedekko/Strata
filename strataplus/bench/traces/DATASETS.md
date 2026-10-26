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

## v1.1 (giro 02:34) — sessioni multi-turno e split tune/holdout (proxy CPU, non AMD)

**Split.** Ogni richiesta delle tracce `traces/v11/*.jsonl` ha il campo `split` (anche le righe round):
- `tune` = i 30 prompt di `proxy_30.jsonl` del giro precedente (seed 20261025) + le sessioni sotto (stessi problemi/domande);
- `holdout` = `datasets/holdout_90.jsonl`, generato da `prepare_holdout.py`: **seed 20261026**, 30 ID per dominio
  (code HumanEval, chat MT-Bench 1° turno, edit edit_np), stesse fonti pinnate e stessi template di `prepare_datasets.py`,
  campionati senza reinserimento tra gli ID **non** presenti nel set tune (verificato con assert: intersezione vuota).
  Lista ID, ID esclusi e sha256 delle sorgenti in `datasets/holdout_ids.json`.
- Sull'holdout c'è solo il teacher-forced Dmax=7 (MTP + lookup in ogni posizione, verify T=1): run `holdout_tf_d7`.
  `ref_tokens` = output del run stesso (greedy T=1). Run live sull'holdout: non eseguiti (priorità al tf, per tempo).

**Sessioni** (`prepare_sessions.py`, metadati e sha256 in `datasets/sessions_meta.json`):
- `agent_turns_bench.jsonl`: 10 sessioni edit_np × 3 turni (stessi 10 problemi di `edit_np.jsonl`):
  t0 = istruzione breve + codice originale; t1 = feedback con la test-suite reale del problema (campo `tests`);
  t2 = richiesta di docstring e type hint. `session_id` = `agent-edit_np-…`, id `…#tN`, category `agent_edit`.
- `mtbench2.jsonl`: 10 domande MT-Bench (le stesse di `mtbench.jsonl`) × 2 turni nativi, `session_id` = `mtbench2-N`.
- Turno N>0: contesto = prompt del turno precedente + risposta del turno precedente (nei run base/tf la propria;
  nei run live la y del run base, via `--ref`) + `<|im_end|>` se manca + nuovo turno utente nel template chat.
  Prompt fino a ~9,3k caratteri ⇒ `-c 8192 -b 8192`.
