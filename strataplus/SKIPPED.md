# File esclusi dal backup (generato da sync.sh)

## File > 50M (non committati): path, byte, sha256

## Binari ELF rimossi (output di build, ricostruibili)
    bench/strata-bench/proxy/llama_spec_trace.v11
    bench/strata-bench/proxy/llama_spec_trace.v11.nollamafile
    bench/strata-bench/proxy/llama_spec_trace.v12.nollamafile
    bench/strata-bench/proxy/llama_spec_trace.v14.nollamafile
    bench/strata-bench/proxy/strata_proxy_spec
    logs/tmp_scratch/jg/fin/bug
    logs/tmp_scratch/jg/fin/bug_g
    logs/tmp_scratch/jg/fin/controller_test_gsan
    logs/tmp_scratch/jg/fin/controller_test_plain
    logs/tmp_scratch/jg/fin/controller_test_san
    logs/tmp_scratch/jg/fin/draft_policy_test_gsan
    logs/tmp_scratch/jg/fin/draft_policy_test_plain
    logs/tmp_scratch/jg/fin/draft_policy_test_san
    logs/tmp_scratch/jg/fin/jg
    logs/tmp_scratch/jg/fin/jg_san
    logs/tmp_scratch/jg/fin/joint_gate_test_gsan
    logs/tmp_scratch/jg/fin/joint_gate_test_plain
    logs/tmp_scratch/jg/fin/joint_gate_test_san
    logs/tmp_scratch/jg/fin/pool_source_test_gsan
    logs/tmp_scratch/jg/fin/pool_source_test_plain
    logs/tmp_scratch/jg/fin/pool_source_test_san
    logs/tmp_scratch/jg/fin/spec_start_test_gsan
    logs/tmp_scratch/jg/fin/spec_start_test_plain
    logs/tmp_scratch/jg/fin/spec_start_test_san
    logs/tmp_scratch/jg/fin/suffix_drafter_test_gsan
    logs/tmp_scratch/jg/fin/suffix_drafter_test_plain
    logs/tmp_scratch/jg/fin/suffix_drafter_test_san
    logs/tmp_scratch/jg/jgtest
    logs/tmp_scratch/jg/jgtest2
    logs/tmp_scratch/jg/jgtest_pre
    logs/tmp_scratch/jg/oob_nd
    logs/tmp_scratch/jg/oob_post
    logs/tmp_scratch/jg/oob_pre

## Esclusi dalla scansione segreti (contenuto sospetto, NON pubblicato)

## Esclusi per licenza (decisione del proprietario, 2026-10-26)

Riferimento: `LICENSE_INVENTORY.md` (sha256 2e160c96f86ca192a52a4935fa6c609e854137ccd9b08452d7eac91acfd1dc11,
CSV sha256 80bf8ba8dee7e440ae614a88bca642813ed36fd527b09d23295ecf92604f2acc), sezione 4, più il controllo del 2026-10-26.
Elenco esatto dei percorsi: `strataplus/.gitignore` (stessa lista negli exclude rsync di `sync.sh`); i percorsi e i pattern che contengono il nome del dataset di edit con licenza non pubblicabile (`edit_np`) stanno in un file solo locale letto da `sync.sh` (vedi `REDACTION_2026-10-27.md`).
Questi file sono stati tolti dalla testa di `strataplus-research` il 2026-10-26 e anche dalla storia del branch
(riscrittura con force push del 2026-10-26). Vedi `ERRATA_LICENZE.md`.

| Categoria | File | Motivo |
|---|---|---|
| Dati derivati dal dataset di edit con licenza non pubblicabile (`edit_np`: testi, prompt tokenizzati, ID, metriche per richiesta) | 289 (par. 4b) | licenza in conflitto: card HF alla revisione fissata "MIT" contro LICENSE del repository GitHub (aggiunto in seguito) con una clausola che vieta l'uso come dati di training |
| `bench/e1/policy/results/e1_per_request.csv` | 1 (par. 4a) | ID e metriche per richiesta di Dolly (CC-BY-SA-3.0, share-alike) e MBPP (CC-BY-4.0, attribuzione), più `edit_np` |
| `bench/strata-bench/datasets/subset_ids.json` | 1 (par. 4a) | 26 ID Spec-Bench (dati da fonti con licenze miste, non verificate) più `edit_np` |
| `logs/tmp_scratch/gen/gen.py` | 1 (trovato il 2026-10-26, fuori dal par. 4) | contiene 2 ID `edit_np` e la diagnosi per richiesta del dominio edit |
| Artefatti H-CA stimati su `edit_np`: `policy/strata-policy/replay/results/v2/hca/` tranne `hca_results.json` e `REPORT.md` (aggregati, pubblicati), comprese le sottocartelle dei modelli stimati; `replay/run_hca.json`; smoke/probe H-CA da /tmp; pesi/feature di classificatori; qualsiasi percorso che contiene il nome del dataset | pattern, anche per file futuri | uso solo locale; si pubblicano gli aggregati, i run file addendum e il codice (`hca*.py`) |
| File il cui contenuto o percorso contiene il nome del dataset (ID compresi), qualunque nome; per ora `bench/traces/mtp_cap_prefix_check.json`, `bench/strata-bench/runs/live_combo_aprime_holdout.md`, `logs/tmp_scratch/mcp_test.json`, `logs/tmp_scratch/order.txt` (mai pubblicati) | guardia sul nome in `sync.sh` (pattern dal file solo locale) | ID e metriche per richiesta |
| `bench/strata-bench/datasets/specbench.jsonl` | regola già esistente | Spec-Bench, licenze miste |
| `bench/e1/policy/data/` | regola già esistente | Dolly, MBPP, `edit_np`, HumanEval in parquet e tokenizer Qwen |

Totale tolto dalla testa il 2026-10-26: 292 file (291 del par. 4 + `gen.py`).

## Dati grezzi di terzi (regola del proprietario, 2026-10-26 20:05 CET)

"Tutto quello che il team produce va nel backup, ma il contenuto grezzo di dataset di terzi no."
Riferimento: `LICENSE_INVENTORY.md` sezione 7 (sha256 29bfb7c43a13614a1c01f8239dec019e9cae7dc0957549b60b98649c8d53e0c1).
Mai pubblicati (non sono mai arrivati sul fork).

| Esclusi | Motivo |
|---|---|
| `bench/strata-bench/datasets/humanevalfix_9a41762f/` tranne `LICENSE_NOTE.md`, `SHA256SUMS` (parquet per linguaggio, card HF) | dataset grezzo bigcode/humanevalpack, riscaricabile dal pin 9a41762f |
| `bench/strata-bench/datasets/commitpackft_fc56fe33/` tranne `raw_files.sha256`, `select_run.log` (`raw/`, `selected/`, `tokenizer/`, card HF) | dataset grezzo bigcode/commitpackft (licenze per repo miste), riscaricabile dal pin fc56fe33 |
| qualsiasi altra cartella `datasets/*/`: solo `LICENSE_NOTE*.md`, `SHA256SUMS`, `*.sha256`, `*.log` | regola per download futuri |
| `*.parquet`, `*.arrow`, `tokenizer*.json`, `*hf_card*`/`*hf-card*` ovunque | formati di dataset/tokenizer e card HF di terzi |
| `logs/tmp_scratch/nfe_*.jsonl`, `*nofuneval*` | NoFunEval: codice di terzi (repo GitHub, PIE/CodeNet, CodeQL), licenze non verificate |
| `logs/tmp_scratch/hfcards/` | copie di card HF di terzi |
| `logs/tmp_scratch/c0.json`, `c1.json` | dump API HF (commit dei repo bigcode, utenti), non prodotti dal team |
| quarantena: file NUOVI sotto `datasets/`, `*.jsonl` nuovi in `tmp_scratch/`, parquet/arrow | fuori finche' non revisionati (sha256 in `REVIEWED` in `sync.sh`) |

Pubblicati dopo revisione: `holdout_90_codechat.jsonl`, `proxy_30_codechat.jsonl` (solo HumanEval MIT + MT-Bench Apache-2.0, nessuna riga
`edit_np`), `commitpackft_selection_manifest.csv` e `commitpackft_selection_counts.json` (solo ID, licenza dichiarata e conteggi, nessun codice).

### Rimossi in questo sync dal controllo licenze/quarantena
    strataplus/bench/traces/raw/v11/tracer_v14_build_info.txt
