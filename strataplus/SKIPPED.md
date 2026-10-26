# File esclusi dal backup (generato da sync.sh)

## File > 50M (non committati): path, byte, sha256
    /workspace/strata-bench/datasets/commitpackft_fc56fe33/raw/java/data.jsonl	57628439	c51a331320f4220d6053e3389485916c738fcaccfd583298b7738af834fa19b9
    /workspace/strata-bench/datasets/commitpackft_fc56fe33/raw/javascript/data.jsonl	128001108	968688a1163c2dbbced0d0f9cf1dd52bc0b626c2ad9b02ff23f5700b2e277f25
    /workspace/strata-bench/datasets/commitpackft_fc56fe33/raw/python/data.jsonl	135858935	d167da37e1058371c48e057cd8815d03700c867dd8bcf58e61420d4dcd288d73

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
    bench/strata-bench/datasets/commitpackft_fc56fe33/raw/c#/data.jsonl
    bench/strata-bench/datasets/commitpackft_fc56fe33/raw/rust/data.jsonl
    bench/strata-bench/datasets/commitpackft_fc56fe33/raw/typescript/data.jsonl
    logs/tmp_scratch/nfe_maintainability.jsonl

## Esclusi per licenza (decisione del proprietario, 2026-10-26)

Riferimento: `LICENSE_INVENTORY.md` (sha256 2e160c96f86ca192a52a4935fa6c609e854137ccd9b08452d7eac91acfd1dc11,
CSV sha256 80bf8ba8dee7e440ae614a88bca642813ed36fd527b09d23295ecf92604f2acc), sezione 4, più il controllo del 2026-10-26.
Elenco esatto dei percorsi: `strataplus/.gitignore` (stessa lista negli exclude rsync di `sync.sh`).
Questi file sono stati tolti dalla testa di `strataplus-research` il 2026-10-26 ma **restano nei commit precedenti**
(la riscrittura della storia non è ancora autorizzata). Vedi `ERRATA_LICENZE.md`.

| Categoria | File | Motivo |
|---|---|---|
| Dati derivati da edit_np (testi, prompt tokenizzati, ID, metriche per richiesta) | 289 (par. 4b) | licenza in conflitto: card HF @<revisione non pubblicata> "MIT" contro LICENSE GitHub edit_np una licenza con una clausola che vieta l'uso come dati di training |
| `bench/e1/policy/results/e1_per_request.csv` | 1 (par. 4a) | ID e metriche per richiesta di Dolly (CC-BY-SA-3.0, share-alike) e MBPP (CC-BY-4.0, attribuzione), più edit_np |
| `bench/strata-bench/datasets/subset_ids.json` | 1 (par. 4a) | 26 ID Spec-Bench (dati da fonti con licenze miste, non verificate) più edit_np |
| `logs/tmp_scratch/gen/gen.py` | 1 (trovato il 2026-10-26, fuori dal par. 4) | contiene 2 ID edit_np e la diagnosi per richiesta del dominio edit |
| Artefatti H-CA stimati su edit_np: `policy/strata-policy/replay/results/v2/hca/` tranne `hca_results.json` e `REPORT.md` (aggregati, pubblicati), quindi anche `edit_np_fitted/`; `replay/run_hca.json`; smoke/probe H-CA da /tmp; pesi/feature di classificatori; qualsiasi nome con "edit_np" (es. `lang_inventory_edit_np/`) | pattern, anche per file futuri | uso solo locale; si pubblicano gli aggregati, i run file addendum e il codice (`hca*.py`) |
| File con ID edit_np nel contenuto (`edit_np-N`), qualunque nome; per ora `bench/traces/mtp_cap_prefix_check.json`, `bench/strata-bench/runs/live_combo_aprime_holdout.md`, `logs/tmp_scratch/mcp_test.json`, `logs/tmp_scratch/order.txt` (mai pubblicati) | controllo sul contenuto in `sync.sh` | ID e metriche per richiesta |
| `bench/strata-bench/datasets/specbench.jsonl` | regola già esistente | Spec-Bench, licenze miste |
| `bench/e1/policy/data/` | regola già esistente | Dolly, MBPP, edit_np, HumanEval in parquet e tokenizer Qwen |

Totale tolto dalla testa il 2026-10-26: 292 file (291 del par. 4 + `gen.py`).
