# Run file v3 — (a') vs default (a), live con arbitro, holdout 90, con A/B tok/s (proxy CPU, non AMD, llama.cpp non Strata)
**Versione 3** (27/10/2026 CET). Parte da `live_combo_aprime_holdout_v2.md` (sha256 3d734b32…) e `run_live_combo_aprime_holdout_v2.sh`
(e1140052…), **non modificati** (sha verificati il 27/10). Script: `runs/run_live_combo_aprime_holdout_v3.sh`,
sha256 **11433cdfd87ed0e5da6e75a2d301e86562caa595a1f8464006912d42d8eb72fd**. Tool nuovo: `tools/aprime_toks_ab.py`,
sha256 **7e1a2dcdd757421bed5939878f5647d42e792f68a5540aa0cafd3cc51eddb0fc** (py_compile ok; provato solo su dati sintetici in /tmp, poi cancellati).
**Scritto e hashato, NON lanciato** (bash -n ok). Si lancia solo su richiesta esplicita, in una finestra annunciata:
`cd /workspace/strata-bench && nohup bash runs/run_live_combo_aprime_holdout_v3.sh &`. Se si lancia la v3, la v2 non si lancia.
Il dominio edit (dataset con licenza non pubblicabile) qui si chiama `edit_np`. Il tag nei nomi dei file è `STRATAPLUS_EDIT_TAG` (env,
oppure il file locale `/workspace/lic_rm/edit_dataset.env`), indicato sotto con `<ET>`.

## 0. Cosa cambia rispetto alla v2
1. **A/B tok/s a coppie alternate**: dopo il TF cap 3 i due bracci live girano 4 volte ciascuno nell'ordine **A1 B1 B2 A2 A3 B3 B4 A4**
   (A = (a'), B = default (a)); coppia i = (A_i, B_i). Tutto nella cartella nuova `traces/raw/aprime_holdout_v14_ab/` (quella della v2 non si usa).
2. Vale anche come **A/B flag-only `--spec 8 --mtp-max-t 4`** (equivalente Strata di (a')) contro la baseline default (a) (`--spec 4 --spec-min-p 0.5`):
   stesso binario, cambiano solo i flag `--live-src`.
3. **Greedy dopo ogni passata** (da B1 in poi), su tutte le passate fatte: un solo prompt diverso ferma tutto (file `STOPPED_greedy`).
4. **Pre-check del cap** esplicito (`cap_precheck.txt`), registrazione di hardware e versioni, `cpu_busy_bench.log` scritto direttamente se il mirror non è vivo.
5. Tag edit letto da `STRATAPLUS_EDIT_TAG` (nessun nome del dataset nello script); soglie del Lead (sez. 5) fissate **prima** dell'hash.

## 1. Bracci e flag
Come la v2 sez. 1 (tabella dei bracci, flag comuni, arbitro sez. 4, deviazioni sez. 5, campi sez. 7): **invariati**.
`FL = -m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7 --spec-draft-n-max 3`
| fase | tag (codechat / edit) | argomenti |
|---|---|---|
| 0 | `holdout_tf_cap3_v14` / `holdout_tf_cap3_v14_<ET>` | `--mode tf --live-src mtp` |
| A_i | `aprime_r<i>` / `aprime_r<i>_<ET>` | `--mode live --live-src aprime --ref ref_holdout_tf.tsv` |
| B_i | `default_a_r<i>` / `default_a_r<i>_<ET>` | `--mode live --live-src default_a --ref ref_holdout_tf.tsv` |
Ogni passata = prima `holdout_90_codechat.jsonl` (30 code + 30 chat), poi `holdout_90_<ET>.jsonl` (30 edit). 17 processi llama in tutto (1 + 8 + 8), in fila.
Durata: **non misurata** per il tracer v14 in live. Unico riferimento: le passate holdout_lookup_v12 sui 90 prompt sono durate 6,5–11 min
(campaign.log 25/10, START/END n7 07:04:58–07:11:27, n16 07:18:33–07:29:34 CET; tracer v12, altra modalità, quindi solo un ordine di grandezza).

## 2. Controlli dello script, in ordine
1. sha256 di tutti gli input (binario, sorgente tracer, arbitro .hpp/.py, prompt, ref, TF7, libllama-common, modello,
   mtp_cap_prefix_check.json, i 5 tool). Se uno non coincide, stop.
2. Nessun altro processo llama (anche prima di ogni passata); `e4v14.done` presente.
3. **Pre-check del cap:** `traces/mtp_cap_prefix_check.json` ha `all_pairs` = 5210 coincidenti su 5389 posizioni con lo stesso contesto,
   `all_100pct` = false (letto il 27/10). La condizione non è al 100%, quindi si rigenera il TF a cap 3 (fase 0).
4. Registrazione in `build_env_info_<ET>.txt`: `uname -a`, `lscpu`, `nproc`, `free -m`, loadavg, gcc/cmake/python, commit llama.cpp e numero di file
   modificati, opzioni GGML_LLAMAFILE/GGML_NATIVE/CMAKE_BUILD_TYPE della build, env STRATA/GGML/LLAMA/OMP (senza le variabili private), sha256 e ldd.
   Comandi esatti in `cmds_<ET>.txt`.
5. Prima di ogni passata: `cpu_foreign.py wait 30 0.5 3600` (CPU libera), poi monitor ogni 2 s e `cpu_judge` a fine passata.
6. START/END in `campaign.log`; in `cpu_busy_bench.log` tramite `tools/bench_window_log.py` (PID 321436 vivo il 27/10 13:3x CET) o, se il mirror
   non è vivo all'avvio, scritti dallo script nello stesso formato.
7. Un solo llama, `nice -n 19`, `-t 6`. `STRATA_DRAFT_VOCAB` tolto dall'env.

## 3. Post (nessun llama)
- `validity_cand_mtp_live_vs_tf_{codechat,<ET>}.json`: cand.mtp live (rep 1) contro TF cap 3 e TF cap 7, come nella v2 (1).
- `aprime_post_{codechat,<ET>}.json`: coerenza dell'arbitro, AL e greedy contro ref sulla rep 1, come nella v2 (2)-(4).
- `toks_ab_{codechat,<ET>}.json` (solo aggregati per dominio) e `.perprompt.json` (per prompt; per l'edit il nome ha `<ET>`).
  - tok/s = output_tokens / decode_ms (prefill escluso). Per prompt si usa il decode_ms medio sulle 4 ripetizioni di ciascun braccio.
  - Per dominio il valore è somma/somma, guadagno = tok/s(a') / tok/s(a) − 1.
  - IC95: bootstrap percentile per prompt (10000 ricampionamenti, seed 20261027).
  - Varianza: guadagno di ogni coppia, deviazione standard fra le coppie, CV fra le ripetizioni di ciascun braccio.
- `aprime_ab_decision_<ET>.json`: applica le soglie della sez. 5. Ha `<ET>` nel nome perché contiene aggregati del dominio edit.
- `MANIFEST_<ET>.sha256` e `aprime_ab_v3.done`.

## 4. Limiti (da citare con ogni numero)
- **proxy CPU, non AMD, llama.cpp non Strata.** I tok/s sono quelli del tracer v14 su CPU (6 thread, nice 19), con la scrittura delle tracce
  per round e i candidati di entrambe le sorgenti calcolati in entrambi i bracci: **non** sono tok/s di Strata né di llama-server.
- Il GO-proxy (sez. 5 iii) non vale come GO di P0: P0 si decide solo su AMD (AMD_PROTOCOL_v4 sez. 11).
- 30 prompt per dominio: l'IC95 bootstrap per prompt non tiene conto della varianza fra ripetizioni, che si riporta a parte (sez. 3).
- Deviazioni dell'arbitro proxy: v2 sez. 5, invariate.

## 5. Soglie del Lead (fissate prima dell'hash di questo file)
- **(i) Validità del confronto.** AL di (a') entro **±3%** dal replay di Policy su `holdout_tf_d7` (somma/somma, domini code ed edit) **e**
  coerenza dell'arbitro **≥ 99% dei round** (entrambi i bracci, entrambe le passate). Vale anche la validità cand.mtp della v2 (1) al 100%.
  Il riferimento del replay è il run file di Strata Policy, **ancora da fissare**: non esiste oggi su disco (cercato in /workspace/strata-policy/replay il 27/10).
  Lo script lo legge da `POLICY_REPLAY_REF` (JSON `{"AL": {dominio: valore}}`) con `POLICY_REPLAY_REF_SHA256`. Se manca o lo sha non coincide,
  (i) non è soddisfatta. **Se (i) fallisce, l'A/B si riporta ma non decide.**
  Nota: la v2 (0) chiede il replay sul TF cap 3 rigenerato perché la condizione cap-prefix non è al 100%. La soglia del Lead nomina holdout_tf_d7:
  se il replay disponibile è sul cap 3, va detto nel report.
- **(ii) Greedy identico al 100%** fra tutte le ripetizioni di entrambi i bracci. **Un solo prompt diverso ferma tutto** (bug). Lo script si ferma.
- **(iii) GO-proxy:** guadagno tok/s **≥ +3% su code e su edit**, ciascuno con **limite inferiore IC95 > 0** (bootstrap per prompt), e
  **chat entro −1%** (stima puntuale). Per l'edit solo aggregati, e solo in file con `<ET>` nel nome.
- **(iv)** Il GO-proxy **non cambia il default**. Con GO-proxy P0 va **in testa** alla misura AMD; senza GO-proxy P0 resta **in coda** AMD.

## 6. Stato
- Scritto, hashato, `bash -n` ok. **Nessun lancio**, nessun processo llama, nessuna traccia prodotta in questo giro.
- Prima del lancio servono: finestra annunciata, `POLICY_REPLAY_REF` fissato (altrimenti (i) non valutabile), nessuna build in corso.
