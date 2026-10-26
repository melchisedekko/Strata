# Strata+ — backup del lavoro di ricerca (speculative decoding)

Questa cartella è un **backup** del lavoro del team Strata+ (Lead, Scout, Bench, Policy) sullo
speculative decoding di Strata per Qwen3.8-Flash-Next: piani, analisi, codice nuovo, patch, test,
benchmark, trace e log. **Non è codice da mergiare**: il branch `strataplus-research` parte da
upstream `Niko1221/Strata@7dd5cf18e68c639a8773e096c5c79f971ea2a9f5` e aggiunge solo `strataplus/`.
Il resto del repo è identico a 7dd5cf1.

## Struttura

| Cartella | Contenuto |
|---|---|
| `plan/` | `piano.md`, `log_format.md`, `PLAN_PAGE.md` (export della Page del piano) |
| `policy/strata-policy/` | lavoro Policy: simulatori, replay, parametri congelati, test, note |
| `scout/` | analisi Scout (`strata-plus/`), workspace scout (senza i clone upstream), riferimenti (`refs/`) |
| `bench/` | harness di benchmark (`strata-bench/`), trace (`traces/`), esperimento E1 (`e1/`) |
| `logs/` | log dei benchmark, log `cpu_busy_*`, file di lavoro recuperati da `/tmp` (`tmp_scratch/`) |
| `patches/` | tutte le patch `.diff`/`.md`, serie `format-patch` e `git bundle` per branch |
| `MANIFEST.sha256` | sha256 di ogni file del backup |
| `SKIPPED.md` | file esclusi: >50 MB (con path, dimensione, sha256), binari ELF, file segnalati dallo scan segreti, file esclusi per licenza |
| `ERRATA_LICENZE.md` | correzioni alle licenze dichiarate in `DATASETS.md` (edit_np, Spec-Bench, E1) |
| `.gitignore` | percorsi esclusi per licenza |
| `SECRET_SCAN_ALLOWLIST.txt` | falsi positivi dello scan segreti verificati a mano (sono hash sha256 di file, non chiavi) |
| `sync.sh` | script di sincronizzazione idempotente |

## Ripristinare i branch delle patch

I branch locali `strataplus-policy-local` (P1–P6, head `e467f6e`) e `strataplus-pt12-measure`
(P-T12 measure v1–v3, head `e441f3a`) sono **pubblicati così come sono** come branch separati di questo
fork (`git fetch origin strataplus-policy-local strataplus-pt12-measure`). In più, come copia di riserva,
sono salvati in `patches/branches/<branch>/` come `git bundle` (thin, prerequisito 7dd5cf1) e come serie
`format-patch` (`7dd5cf1..head`). `LOG.txt` e `HEAD` riportano commit e head attesi.

Da un clone di questo repo (che contiene già 7dd5cf1):

```bash
# metodo 1: bundle
git fetch strataplus/patches/branches/strataplus-policy-local/strataplus-policy-local.bundle \
    strataplus-policy-local:strataplus-policy-local
git fetch strataplus/patches/branches/strataplus-pt12-measure/strataplus-pt12-measure.bundle \
    strataplus-pt12-measure:strataplus-pt12-measure

# metodo 2: git am (copiare prima le patch fuori dal working tree, perché il checkout le rimuove)
cp -r strataplus/patches/branches /tmp/sp-branches
git checkout -b strataplus-policy-local 7dd5cf18e68c639a8773e096c5c79f971ea2a9f5
git am /tmp/sp-branches/strataplus-policy-local/format-patch/*.patch
```

⚠️ **Non mergiare insieme** `strataplus-policy-local` (P6, engine hook) e `strataplus-pt12-measure`
(P-T12): entrambi modificano `generate.cpp` e vanno in conflitto. P-T12 è una patch di sola misura,
non per produzione. Vedi anche `patches/strata-policy/STATUS_P6_NON_ACCENDERE.md`.

`patches/llama.cpp/worktree_uncommitted.diff` contiene le modifiche non committate al clone llama.cpp
(`common/speculative.cpp/.h`, base `d327bf1`).

## Dataset e licenze

| Dataset | Origine | Licenza | Stato |
|---|---|---|---|
| HumanEval | openai/openai_humaneval @7dce605 | MIT | incluso |
| MT-Bench questions | lm-sys/FastChat @587d5cf `question.jsonl` | Apache-2.0 | incluso (anche nei mix proxy_30, check_v12, holdout, sessions_all, mtbench2) |
| edit_np | edit_np @<revisione non pubblicata> | **licenza in conflitto** (non "MIT"): la card HF alla revisione usata dice MIT, il `LICENSE` del repo GitHub edit_np dice una licenza con una clausola che vieta l'uso come dati di training | **escluso** dal 2026-10-26 (testi, prompt tokenizzati, ID, metriche per richiesta, artefatti H-CA); usato solo in locale. Vedi `ERRATA_LICENZE.md` |
| Sessioni agent (agent_v12*) | repo Strata | MIT | incluso |
| Spec-Bench | hemingkx/Spec-Bench @fd2c1cd | repo Apache-2.0, contenuto da fonti con licenze miste | **escluso**: `specbench.jsonl` non è mai stato pubblicato; fino al 2026-10-26 però `bench/strata-bench/datasets/subset_ids.json` conteneva 26 ID `specbench-N` (solo ID). Il file è stato tolto dalla testa il 2026-10-26 |
| E1 `policy/data` (dolly, mbpp, tokenizer Qwen) | Hugging Face | CC-BY-SA-3.0 / CC-BY-4.0 / altro | **escluso** (riscaricabile). Anche `e1_per_request.csv` (ID e metriche per richiesta di Dolly e MBPP) è stato tolto dalla testa il 2026-10-26; restano solo gli aggregati (`e1_summary.json`, `E1_results.md`) |

> **Nota del 2026-10-26 (licenze).** Dalla testa di questo branch sono stati tolti 292 file: i 291 della sezione 4 di
> `LICENSE_INVENTORY.md` (sha256 2e160c96f86ca192a52a4935fa6c609e854137ccd9b08452d7eac91acfd1dc11; 289 derivati da edit_np,
> `e1_per_request.csv`, `subset_ids.json`) più `logs/tmp_scratch/gen/gen.py` (ID edit_np). Sono elencati in `.gitignore`
> e negli exclude di `sync.sh`. **Questi file esistono ancora nei commit precedenti** del branch (fino a `54002c1`):
> la storia non è stata riscritta. Dettagli in `ERRATA_LICENZE.md` e `SKIPPED.md`.

## Cosa non è incluso

- Pesi dei modelli (`*.gguf`, `*.safetensors`, `strata-bench/models`, circa 6,2 GB) e il frammento di header `q4km_head.bin`
- Output di build e binari (`build*/`, `*.o`, `*.so`, eseguibili ELF; vedi `SKIPPED.md`), virtualenv, wheel, header ROCm (`rocm-hdr`)
- Clone completi upstream (Strata, llama.cpp, colibri, HIP-CPU, arctic, sglang, vllm) e copie di documenti upstream
- File >50 MB (elencati in `SKIPPED.md`) e file segnalati dallo scan segreti e non verificati
- Dati derivati da edit_np, ID/metriche per richiesta di Dolly, MBPP e Spec-Bench, classificatore H-CA stimato su edit_np (solo locale; pubblicati solo gli aggregati `hca_results.json` e `REPORT.md`) (vedi `SKIPPED.md`, `ERRATA_LICENZE.md`)

## Sincronizzazione

```bash
GITHUB_TOKEN=... bash /workspace/strataplus-backup/sync.sh     # NOPUSH=1 per solo commit locale
```

Lo script è idempotente:
- usa rsync con gli stessi exclude e il limite di 50 MB
- rigenera bundle e format-patch solo se cambia la head
- esegue lo scan segreti (regex + gitleaks)
- rigenera `MANIFEST.sha256`
- committa solo se ci sono cambiamenti, con timestamp CET
- fa push dei branch `strataplus-research`, `strataplus-policy-local` e `strataplus-pt12-measure` del fork `melchisedekko/Strata`, solo in fast-forward e dopo lo scan segreti dei commit (mai il branch di default)

Il token viene letto da `GITHUB_TOKEN` solo a runtime e passato tramite header HTTP: non viene mai scritto in file, config o URL.
**Non eseguire lo script con `bash -x`**, perché la traccia stamperebbe il token.
