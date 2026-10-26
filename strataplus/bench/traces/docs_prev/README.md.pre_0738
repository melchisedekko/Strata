# Tracce strataplus.v1 — **proxy CPU, non numeri AMD**

Tutto in questa cartella è misurato su CPU con un modello **denso** piccolo (Qwen3.5-2B MTP) tramite llama.cpp, come proxy
per il replay di Strata Policy. Nessun numero qui è un numero AMD né di Qwen3.8-Flash-Next. I tempi CPU valgono solo come
rapporti relativi (speedup, s(T), rho). Niente push, niente PR: patch solo locali.

## File
- `*.jsonl` — tracce annotate schema `strataplus.v1` (righe `request` + `round`); originali grezzi in `raw/` (+ `.err`, `campaign.log`).
  - `tf_d7` — teacher-forced: in **ogni** posizione di y (= output base) candidate MTP a Dmax=7 con probs + lookup, accettazione controfattuale vs y.
  - `base_r{0,1,2}`, `live_mtp_k3_r*`, `live_lookup_r*`, `live_combo_k3_r*` — ABBA a blocchi, 3 ripetizioni (ordine diretto/inverso alternato).
  - `live_mtp_k{1,2,5,7}_r0` — per il gate V1. Ogni round live contiene comunque `cand.mtp` e `cand.lookup` (G1 in LOG_SCHEMA).
  - `raw/diag_yright`, `raw/diag_ywrong` — diagnosi greedy (12 prompt), `raw/p4_*` — profilo costi.
- `SUMMARY.md` / `summary.json` — punti critici, diagnosi greedy, AL, speedup, V1, P4. `GREEDY_DIAG.md` / `greedy_diag.json`, `CRITICAL.md`.
- `cost_p4_cpu.json` — profilo P4 (**proxy CPU, modello denso, non AMD**).
- `DATASETS.md`, `LOG_SCHEMA.md` (divergenze G1–G10), `models.sha256`, `annotate_report.json`.

## Setup misurato
- CPU: Intel Xeon Processor, 8 CPU, 1 thread/core; RAM 16002 MB, no swap, no GPU. Run con `-t 6`.
- RAM all'avvio campagna: 10923 MB free / 12790 MB available; max RSS del processo (2B Q4_K_M, tf, -c 4096) misurato: 1741 MB.
- llama.cpp `d327bf1f0780f87b8c01b367b61853b0c291d7c4` + patch locale `strata-bench/patches/llamacpp-draft-mtp-probs.patch`
  (common/speculative.{cpp,h}: espone le probs top-1 del draft MTP). Proxy: `strata-bench/proxy/llama_spec_trace.cpp` (copia in `patches/`).
- Strata `7dd5cf18e68c639a8773e096c5c79f971ea2a9f5`: lookup = `strata::spec::SuffixDrafter` reale.
- Modelli (solo GGUF testo, nessun mmproj), sha256 in `models.sha256`:
  - `qwen35-2b-mtp-q4_k_m.gguf` 1,329,851,808 B (unsloth/Qwen3.5-2B-MTP-GGUF) — usato per tutte le tracce.
  - `qwen35-0.8b-mtp-q4_k_m.gguf` 549,698,976 B, `qwen35-0.8b-mtp-q8_0.gguf` 833,592,736 B — solo P4.
- Flag comuni: `--spec-type draft-mtp -t 6 --temp 0 -n 128 -c 4096 -b 4096 -ub 512 --no-repack --dmax 7`; comandi in `strata-bench/run_traces.sh`,
  `run_p4.sh` (`raw/p4_cmd.txt`), `run_diag.sh`. Post-processing: `tools/annotate.py`, `tools/summarize.py`, `tools/greedy_diag.py`, `tools/cost_p4.py`.
- Campagna: 01:26:57 → 02:29:20 CEST (2026-10-25).

## P4 — proxy CPU, modello denso, non AMD
s(T) = mediana tempo forward a T token / forward a T=1 (3 warmup, 20 ripetizioni, ordine T alternato, rollback checkpoint),
rho_mtp = pendenza costo draft MTP per profondità / step T=1, rho_lu = costo `SuffixDrafter::propose(7)` / step. IC95 bootstrap in json.
Un modello denso su CPU non ha la struttura MoE/routing di Qwen3.8-Flash-Next né i kernel AMD: forma di s(T) e rho **non trasferibili**.

## Limiti e anomalie note
- Identità greedy con baseline T=1 non garantita su CPU (G8, misurato in GREEDY_DIAG.md).
- Bug fine sequenza (G9): round esclusi da AL/V1, binario non corretto.
- `live_combo_k3` = MTP k≤3 | lookup ≤7: AL fino a 8 per round.
- Carico concorrente: `run_v2.py` (Strata Policy) attivo da 02:07 CEST durante combo_r2, k1/k2/k5/k7, P4, diag.
- Outlier di tempo (stalli): speedup robusto esclude 2 coppie. P4 Q8_0: s(8) < s(7) (2.2527 vs 2.3609), non spiegato.
- La patch di trace Strata (`patches/strata-plus-trace.patch`) non è compilata/eseguita qui (nessun AMD/HIP).
