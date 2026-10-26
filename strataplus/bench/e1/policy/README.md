# E1 — output di Strata Policy (H2, limite superiore model-free)

Cartella mia; i file di Strata Bench in `/workspace/strata-plus/e1/` (fuori da `policy/`) non sono toccati.

- `e1.py` — esperimento: richieste reali (HumanEval 164 + MBPP test 500 = `code`; Dolly-15k 400 campionate seed 0 = `chat`;
  edit_np 105 = `edit`; storia git di Strata @ 7dd5cf18, file con ≥8 commit, y = lato nuovo degli hunk = `session_full`
  (prompt con file intero) e `session_excerpt` (prompt con soli estratti)). Tokenizer Qwen3.5-2B (`data/tok_Qwen3.5-2B`).
  Lookup e pool usano il `SuffixDrafter` di PRODUZIONE (`/workspace/strata-policy/replay/native/libstrata_spec_capi.so`,
  compilato con zig c++ da `/workspace/strata-src` @ 7dd5cf18, min_match 3, max_match 64 come il motore).
- `e1_report.py` — aggregazione e IC95 (bootstrap a cluster, appaiato) → `results/E1_results.md`, `results/e1_summary.json`.
- `results/e1_per_request.csv` — contatori per richiesta; `results/pool_sizes.json` — storia dei pool.
- `data/` — dataset scaricati da Hugging Face (licenze: HumanEval MIT, MBPP CC-BY-4.0, edit_np MIT, Dolly CC-BY-SA-3.0).

**Limiti:** y è testo di riferimento, non output greedy di un modello (il modello reale può scrivere altro); niente MTP
(la quota di lookup utile si riduce quando MTP copre già il testo libero); tok/s stimati con profili simbolici (P1/P2 =
stime del codice, non misure; ρ_lu = 0,001 per token, ipotesi ≈20 µs/token); le sessioni git sono una costruzione
(commit come turni di un agente). Rigenera: `../../../strata-policy/.venv/bin/python e1.py && ... e1_report.py`.
