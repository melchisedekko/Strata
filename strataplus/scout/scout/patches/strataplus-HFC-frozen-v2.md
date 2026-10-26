# strataplus H-FC frozen costs — v2

Patch: `strataplus-HFC-frozen-v2.patch` (`git diff 7dd5cf1`, 7 file, 442 inserimenti, 5 cancellazioni),
sha256 f5a02954320b39aaa6f385a3d5536dc9e25c2306d1248ed44ac9e61a6af355b5.
Sostituisce la v1 (`strataplus-HFC-frozen-v1.patch`, sha256 4ab7632926bf...0e344433, invariata).
`git apply --check` (indice temporaneo, nessun checkout): rc=0 su 7dd5cf1 e su b24c6a1.
Numeri di riga: `src/program/generate.cpp` con la v2 applicata (tra parentesi: 7dd5cf1).

## Cosa cambia rispetto alla v1

### (a) Il file di STRATA_SPEC_COST_FROZEN si legge e si valida PRIMA del caricamento del modello (CLI e serve)
- `include/strata/spec/frozen_costs.hpp`: nuova `struct FrozenCosts` (tabella letta e validata, non ancora applicata),
  `validate_frozen_costs`, `parse_frozen_costs_text`, `load_frozen_costs_file(path, S, FrozenCosts&, err)`,
  `apply_frozen_costs(policy, fc, S, err)`. Le API v1 (`apply_frozen_costs_text`, `load_frozen_costs_file(policy, ...)`)
  restano come parse + apply: il test v1 passa invariato.
- `src/program/generate.cpp`:
  - righe 157-188: `g_frozen_costs`, `preload_frozen_costs()` (riga 165: env, regola JOINT_DET, lettura file, sha256,
    validazione; stampa path + sha256) e `load_frozen_costs()` (riga 181: applica la tabella già validata, ri-valida
    contro lo S finale, stampa `cost_table_text()`).
  - **riga 3257**: `preload_frozen_costs(o.spec, ...)` in `main()`, subito dopo la risoluzione di `--spec` (blocchi suffix
    e lookup-chain, righe ~3236-3253); se fallisce: `strata generate: ...` / `strata serve: ...` e `return 1`.
    Vale per CLI e serve: è lo stesso `main`, prima della biforcazione `if (o.serve)` (riga 8395).
  - Caricamento del modello, tutto DOPO la riga 3257:
    - riga 3281: metadati del primo shard (`GgufFile meta(o.native_shards.front())`, solo header);
    - riga 3504: `expert_layout_load(o.pack, ...)`;
    - riga 3803: `native_embed.load(...)`;
    - **riga 3938: `wt.load(o.pack, arena, pool_bytes, ...)` (i pesi)**; riga 3948 "MiB of weights loaded".
  - Applicazione alla policy: dove la faceva la v1, riga 11224 (serve, dopo `policy.set_robust`, riga 11223) e
    riga 16490 (CLI, dopo `policy.set_robust`, riga 16489).
  - Unica lettura prima della riga 3257: riga 2435, header per lo switch di famiglia; un file `qwen35moe` va su
    `strata::qwen35::run` (riga 2440), motore separato, non agganciato (non usa DraftPolicy: vedi sotto).
- S: la validazione iniziale usa `o.spec` risolto dagli argomenti; dopo può solo SCENDERE (cap di `--draft dflash2`,
  riga 5543 `o.spec = cap`) e `apply_frozen_costs` ri-valida contro lo S finale. Differenza dalla v1: con il cap
  dflash2, un file che copre T1..cap ma non T1..--spec ora viene rifiutato all'avvio.

### (a2) Regola nuova: STRATA_SPEC_COST_FROZEN + STRATA_SPEC_JOINT_DET
- In `preload_frozen_costs` (quindi prima del modello, CLI e serve): se `STRATA_SPEC_COST_FROZEN` è non vuota e
  `STRATA_SPEC_JOINT_DET` è non vuota e diversa da `0`, rc=1 con
  `strata generate|serve: STRATA_SPEC_COST_FROZEN e STRATA_SPEC_JOINT_DET=<v> sono entrambe impostate: non si combinano
  (togliere una delle due, o STRATA_SPEC_JOINT_DET=0)`. Il controllo precede la lettura del file. In 7dd5cf1
  `STRATA_SPEC_JOINT_DET` non esiste (rg: 0 occorrenze): si guarda solo l'env.

### (b) SYCL
- `sycl/src/program/generate.cpp` righe 1735-1737 (in `main`, dopo `--version`): se `STRATA_SPEC_COST_FROZEN` è
  impostata e non vuota, stderr `strata: warning: STRATA_SPEC_COST_FROZEN ignorata su SYCL (<path>)`. Nient'altro.
  Non compilato (nessun compilatore SYCL sul box).

## Copertura dei percorsi per Qwen3.8-Flash-Next (lettura di 7dd5cf1)
- Architettura GGUF: `qwen4exp` (`include/strata/artifact/model_family.hpp` righe 3, 17, 22, 30-31, 43-44:
  "Qwen3.8-Flash-Next, `qwen4exp`"; `model_family_runs` riga 54 = solo Qwen4Exp; `docs/AMD_HIP.md:852`).
  Quindi NON passa dallo switch `qwen35` (generate.cpp 7dd5cf1 righe 2396-2408): gira sul percorso principale di `main`.
- DraftPolicy compare solo in `src/program/generate.cpp` (più draft_policy.hpp/.cpp; rg su src, include, metal, sycl,
  serve: nessun altro uso). Due istanze sole, nessuna riassegnazione (`policy =` assente):
  - serve: riga 11219 (11178) `DraftPolicy policy(S)` nel blocco `if (o.serve)` (8395 / 8354), "learned over the whole
    process"; aggancio H-FC riga 11224. Usi:
    - pipeline T (`--pipeline-windows`, `pl_pw = pipe ? o.pipeline_windows : 0`, riga 13124 / 13082): `choose` 14513 (14471),
      `observe` 14801 (14759);
    - loop GEN seriale (`while (!pl_ran && !cancelled ...)` riga 14922 / 14880): `set_context` 14924 (14882),
      `choose` 14942 (14900), `chain` 14958 (14916), `observe` 15234 (15192), `observe_chain` 15237 (15195);
    - `keep_draft` nella chain rule MTP 11227 (11185).
  - CLI: riga 16471 (16429) `DraftPolicy policy(o.spec)`; aggancio riga 16490; usi 16493 keep_draft, 16580 set_context,
    16603 choose, 16623 chain, 16757-16758 observe / observe_chain.
  - BGEN / `--batch` (slot paralleli, riga 12014 / 11972 e seguenti): nessuna chiamata a DraftPolicy; le bozze degli
    slot (--batch-mtp) non passano dalla policy, quindi H-FC lì non ha effetto (né deve).
- Conclusione: l'aggancio copre tutti i percorsi in cui DraftPolicy::choose/observe sono usati (serve pipeline T,
  serve seriale, CLI), perché ogni uso è sulla stessa istanza già congelata subito dopo `set_robust`. Nessuna modifica
  necessaria per la copertura.
- Osservazione (comportamento di 7dd5cf1, non cambiato): il loop pipeline T non chiama `set_context`, quindi usa il
  bucket lasciato dall'ultimo `set_context` del loop seriale (all'inizio il bucket 0, ctx<6K). Con la tabella congelata,
  sul percorso pipeline T conta di fatto il bucket 0 finché il loop seriale non lo cambia.

## Test (box, CPU host, g++ -O2, nice 19, uno alla volta; log in /workspace/scout/cpu_busy_scout.log)
- `draft_policy_frozen_test` v2 (nuova sezione 5: parse/apply separati, tabella non caricata, S 4->3 accettato,
  S salito oltre la tabella rifiutato, stessa tabella del percorso v1, file inesistente): PASS, rc=0 (prima della regola JOINT_DET, che non tocca questi file).
- `draft_policy_test` originale contro draft_policy.cpp v2: PASS, rc=0.
- Scenario hook v2 (`/workspace/scout-local/hfc_identity_v2/hook_scenarios_v2.sh`; `hook_main_v2.cpp` contiene il testo
  delle funzioni v2 estratto da generate.cpp, ordine preload -> MODEL_LOAD -> policy+apply), CLI e serve:
  24/24 come atteso, rc=0. Errori (bad_bucket, bad_t, file inesistente, FROZEN+JOINT_DET=1/yes,
  bad_t+JOINT_DET=1) -> rc 1 SENZA la riga MODEL_LOAD; JOINT_DET=0 o vuota, oppure FROZEN vuota -> rc 0.
- Build HIP gfx1100 (clang 17 / HIP 5.7.31921), fatta prima della regola JOINT_DET: `generate.cpp.o` e
  `libstrata_spec.a` v2 rc=0, warning identici a 7dd5cf1. Dopo la regola JOINT_DET generate.cpp non è stato
  ricompilato in HIP (le build HIP sono rinviate: `/workspace/scout-local/hfc_hip_build_deferred.sh v2`).

## Differenza v1 -> v2
`diff -u v1.patch v2.patch`: /workspace/scout-local/v1_v2.interdiff (292 righe). frozen_costs.hpp 115 -> 168 righe;
generate.cpp +20 -> +45 righe; draft_policy_frozen_test.cpp + sezione 5; sycl/src/program/generate.cpp +3 (nuovo).
draft_policy.hpp, draft_policy.cpp, CMakeLists.txt identici alla v1.
