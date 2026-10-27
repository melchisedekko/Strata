# Redazione del nome del dataset di edit (2026-10-27)

Su decisione del proprietario, nessun file pubblicato in questo branch nomina più il dataset di edit con licenza
non pubblicabile usato nel dominio `edit` (vedi `ERRATA_LICENZE.md` e `SKIPPED.md` per il motivo di licenza).
Al suo posto si usa l'etichetta generica **`edit_np`**; gli URL di download sono sostituiti da `<URL non pubblicato>`.

Aggiornamento 2026-10-27 (seconda passata): sono state tolte anche le altre tracce che permettevano di risalire al
dataset. Il dataset correlato dello stesso autore (anch'esso **EXCLUDE**, stesso conflitto di licenza) è indicato solo
così; la revisione HF fissata è sostituita da `<revisione non pubblicata>`, lo sha della card del dataset correlato da
`<sha non pubblicato>`, il commit del `LICENSE` GitHub da `<commit non pubblicato>`, l'eventuale riferimento arXiv da
`<arXiv non pubblicato>`. I valori reali restano solo in file locali; la guardia di `sync.sh` blocca anche questi.
La classificazione e il ragionamento sulle licenze sono invariati. Il codice legge la revisione dalla variabile
`STRATAPLUS_EDIT_DATASET_REV` (o dal file locale), come già l'identificativo.

**Attenzione:** i commit precedenti di questo branch contengono ancora il nome (la storia non è stata riscritta).

## Cosa è cambiato

- **Prosa** (README, piano, report, patch, STATUS, log): nome sostituito con "dataset di edit con licenza non
  pubblicabile" o `edit_np`.
- **Codice** (`prepare_datasets.py`, `prepare_sessions.py`, `prepare_check_v12.py`, `prepare_holdout.py`,
  `tools/check_v12_licenses.py`, `e1.py`, `ceiling_third_source.py`): l'identificativo del dataset, la revisione e
  l'etichetta locale si leggono da variabili d'ambiente (`STRATAPLUS_EDIT_DATASET`, `STRATAPLUS_EDIT_DATASET_REV`,
  `STRATAPLUS_EDIT_NAME`, `STRATAPLUS_EDIT_TAG`) o da un file locale non pubblicato
  (`STRATAPLUS_PRIVATE_ENV`); se mancano, gli script si fermano con un messaggio d'errore esplicito.
- **JSON** (`sessions_meta.json`, `run_hlang_editfix.json`, `ceiling_third_source.json`): chiavi ed etichette → `edit_np`.
- **`sync.sh`**: i pattern che contengono il nome stanno in un file solo locale (`STRATAPLUS_SYNC_PRIVATE`); senza quel
  file il sync non parte. Una guardia mette in quarantena qualsiasi file il cui percorso o contenuto contiene il nome e
  annulla il commit se uno arriva comunque nell'indice.
- **`.gitignore`**: le righe che contenevano il nome sono state spostate nel file solo locale (vengono comunque applicate
  dal controllo licenze di `sync.sh`).

## File redatti solo nella copia pubblicata

Questi file sono congelati (sola lettura) oppure il loro sha256 è registrato altrove (manifest, run file pre-registrati,
asserzioni in `hca_v2.py`/`hca_split.py`, script in coda nella pipeline). L'originale locale **non** è stato modificato:
`sync.sh` sostituisce il nome nella sola copia pubblicata. Quindi lo sha256 pubblicato **non** coincide con quello
registrato nei manifest; la colonna "originale" è quella registrata (e verificabile sulla copia locale).

| File | sha256 originale (locale, registrato) | sha256 pubblicato |
|---|---|---|
| `bench/strata-bench/LANG_COUNT_editfix.json` | `9ea608a83cf2c0da25d925f628b9f5d2be18974ed76fd74c383255431e1c6417` | `0cb0050bcd5990c8601ed8b3c87ab21d94b7020e004f7811fb5fb1af4d9db89d` |
| `bench/strata-bench/LANG_COUNT_editfix.md` | `ba6a419083b5233155c9e471625717d80f97448f97045115dbba8b90d50c8793` | `f66832925019193c6a5a502d127bc83645840f989f721e7915f2793af36010c0` |
| `bench/strata-bench/datasets/humanevalfix_9a41762f/LICENSE_NOTE.md` | `a6ceeb5a076d7f3c1e93134566e926121c4cfb4ee998caed27932417a883e2e2` | `0b67d3f4cd3eefffcf503e74d8d9361a60de39a009ca7a9ff5350db64d8ff674` |
| `bench/strata-bench/runs/live_combo_aprime_holdout_v2.md` | `3d734b32f979b4cd952547d0ae8cf9f1b4cdf29e91b9b7b154bc0ed3cbba0e04` | `50e8bdde921f6a90c5bb7cf3b5b65e0b46f9e724f27f2916706d547eb786c714` |
| `bench/strata-bench/runs/run_live_combo_aprime_holdout_v2.sh` | `e1140052619d4dd9c672c96f0926f0399c113f21382595d6e7f2813067c51ace` | `d25c3373c9df67449e80e3f2228bbeeaa859b67ac39af06dff60eb0d3d8c7611` |
| `bench/strata-bench/tools/lang_count_editfix.py` | `3a75dd860a1d438789d6192f27be7a5af9175b39fc8ffd1d4a95a63685b782cd` | `47042a1443f6d428f271a43d91bcbc9e6f56d477eec8c6f73ef36b8efdd57c7c` |
| `bench/strata-bench/tools/post_holdout_lookup_v12.py` | `f37ec8f69461ff40a14a3881e60a91d798a89408e087457a916664eb864014e1` | `cd8bc39d5709de13598c3c70ed64f7c6d3f1aa00bf71a9bd1fd395ecce6697d9` |
| `bench/strata-bench/run_e4_v14.sh` | `8da5f5f748cf709a12b67ca45e63018ae59867a098f5f863ce3b78ac740b6ff0` | `4fe031d3af57298c10fefe9f9d2bfae894262ef88db0c64cb6906cbaf7a9b1e8` |
| `bench/strata-bench/LICENSE_INVENTORY.md` | `29bfb7c43a13614a1c01f8239dec019e9cae7dc0957549b60b98649c8d53e0c1` | `f41812ecbf9d5ee494ca865eef15958f84e6ef367dcdcce9e860bb858b3a9faa` |
| `bench/strata-bench/LICENSE_INVENTORY.csv` | `80bf8ba8dee7e440ae614a88bca642813ed36fd527b09d23295ecf92604f2acc` | `77094a93d2bee113ebac918334f5f1f0f7e637c51f40c36c49357a280c069908` |
| `bench/strata-bench/DATASETS.md` | `5d34e88ffc578aa55a98f00390cfc48a104fc3bfaf6f601b3ce3e21cca08882e` | `d44ebd01b44da0445b12b40877b8bbb9afc4e148e0a6f2b843ca39a5a3c14365` |
| `bench/traces/DATASETS.md` | `f3ad9ab19eee88d514e827fef3c351e5097e025786f96180d2ccd6bbd34784bc` | `50e758fc1aafaf2b7742f0d51955671e77e377c8ab2c1f0ef9a2fe7a0075141e` |
| `bench/traces/AMD_PROTOCOL_v3.md` | `e963d80a02d19cd276ad19f0d1a50dbb629d1b4878baf9fcc48346d87d8ce59f` | `efbd718e53e29a748c4ec47386e4593b09ee070781da400d7eebb4886212cfb4` |
| `bench/traces/docs_prev/LOG_SCHEMA.md.pre_0810` | `8f49ddc4d9065197f7d9be453a1f72f7943e4db4c2d76a1792444c9da011bb56` | `c4b16cbe98ea4f4fc7fd24bbfad2bd3fb3bfa871b34ee4a9f8cc0e85e100c681` |
| `bench/traces/holdout_lookup_v12/post_holdout_lookup_v12.py` | `f37ec8f69461ff40a14a3881e60a91d798a89408e087457a916664eb864014e1` | `cd8bc39d5709de13598c3c70ed64f7c6d3f1aa00bf71a9bd1fd395ecce6697d9` |
| `policy/strata-policy/replay/hca_split.py` | `81105c9d3c5663a31623b76e962d18b1fda1381097c16d17a071afc834f97230` | `c596d6074cc229fa5a12f3241104ab282d45e624fc38751105984425185ba32e` |
| `policy/strata-policy/replay/results/v2/hca/REPORT.md` | `7cf45552739c015afea01d402eec89696aad92c482989d73ff78d9d41a5daa56` | `5d96c2da6dd372a96c749fd818e9a3c459f36125fb056694cb891e4b02ebb981` |
| `policy/strata-policy/replay/run_hca_addendum1.json` | `c3490e220313ec377e0fbc0f63f0994a228d351d0286b9248ec125a81726c386` | `fd1339b0d6b232d95a1fd667ff735d8ed18bf4669c6c2c143ba49aa5e4bb6f9f` |
| `policy/strata-policy/replay/run_hca_addendum2.json` | `4ac1f236b7bf500760fa444d0c7f34e3810700b5f21236fc419389173fc60e49` | `6131e81c6ce66ad4d7ff402eefb33d5cbc41090880979e72af2c2aaf0939eb44` |

Inoltre, nella sola copia pubblicata, `sync.sh` redige i log del monitor CPU (`cpu_*.log`, `cpu_busy*.log`), che
registrano in tempo reale le righe di comando dei processi e possono quindi catturare il nome (questi log non hanno
sha256 registrati). Qualsiasi altro file che contenga il nome resta fuori dalla pubblicazione (quarantena in `sync.sh`).
