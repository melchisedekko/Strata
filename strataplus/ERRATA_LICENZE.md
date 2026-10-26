# Errata licenze — 2026-10-26

Riferimento: `LICENSE_INVENTORY.md` (sha256 `2e160c96f86ca192a52a4935fa6c609e854137ccd9b08452d7eac91acfd1dc11`),
`LICENSE_INVENTORY.csv` (sha256 `80bf8ba8dee7e440ae614a88bca642813ed36fd527b09d23295ecf92604f2acc`).

`DATASETS.md` (copie in `bench/strata-bench/DATASETS.md` e `bench/traces/DATASETS.md`) non viene modificato, perché il suo
hash è registrato in `MANIFEST.sha256` e nei manifest delle tracce. Questo file lo corregge.

## 1. edit_np: la licenza non è semplicemente "MIT"

`DATASETS.md` e il README indicavano edit_np (HF `edit_np` @<revisione non pubblicata>) come **MIT, incluso**. Non è corretto
presentarlo così: le due fonti upstream sono in conflitto.

- La card Hugging Face alla revisione usata (e su main, tag `license:mit`) dice MIT:
  <URL non pubblicato> Il `LICENSE` del repo GitHub `edit_np`, aggiunto in seguito (commit <commit non pubblicato>), è una licenza con restrizione d'uso per ML. La clausola 4 vieta di usare i contenuti come dati di
  training di modelli di machine learning: <URL non pubblicato> è stabilito quale delle due valga per la revisione @<revisione non pubblicata>. Per questo, per decisione del proprietario, **nessun
contenuto derivato da edit_np viene pubblicato**: testi, prompt tokenizzati, ID, metriche per richiesta e il
classificatore H-CA stimato su edit_np (`results/v2/hca/edit_np_fitted/`, `replay/run_hca.json`, smoke/probe).
edit_np resta utilizzabile solo in locale. Restano pubblicati gli aggregati: `results/v2/hca/hca_results.json`,
`results/v2/hca/REPORT.md` e le medie per dominio `edit` nei report; anche `run_hca_addendum1/2.json` e il codice.

## 2. Spec-Bench: contraddizione corretta

Il README diceva che Spec-Bench era escluso. Il testo completo (`specbench.jsonl`) non è mai stato pubblicato, ma
`bench/strata-bench/datasets/subset_ids.json` conteneva 26 ID `specbench-N` (solo ID, nessun testo). Spec-Bench è
Apache-2.0 come repo, ma i dati provengono da fonti con licenze miste non verificate una per una. Il file è stato tolto
dalla testa il 2026-10-26.

## 3. E1: `e1_per_request.csv`

Il README diceva "restano solo id e numeri in `e1_per_request.csv`". Il file contiene ID e metriche per richiesta di
399 righe Dolly (CC-BY-SA-3.0), 500 MBPP (CC-BY-4.0), 164 HumanEval e 105 edit_np: è stato tolto dalla testa il 2026-10-26.
Restano gli aggregati (`e1_summary.json`, `pool_sizes.json`, `E1_results.md`).

## 4. Cosa è stato fatto il 2026-10-26

- Tolti dalla testa di `strataplus-research` **292 file**: i 291 della sezione 4 dell'inventario (289 solo edit_np,
  più `e1_per_request.csv` e `subset_ids.json`) e `logs/tmp_scratch/gen/gen.py` (2 ID edit_np
  e diagnosi per richiesta del dominio `edit`), trovato da una scansione successiva di tutti i file della testa.
- Percorsi esatti e pattern generici (nomi con "edit_np", artefatti H-CA/classificatore, anche futuri) in
  `strataplus/.gitignore`; gli stessi exclude in `sync.sh`, che controlla anche la copia prima del commit.
- Le copie originali restano in locale (`/workspace/...`), fuori dal repo pubblico.

## 5. Limite: la storia git

**I file tolti esistono ancora nei commit precedenti** del branch `strataplus-research` (gli 8 commit di sync del
2026-10-26, 19:16–19:21 CET, fino a `54002c1`) e sono quindi ancora scaricabili dal fork pubblico. La riscrittura della
storia (con force push) non è ancora autorizzata.
