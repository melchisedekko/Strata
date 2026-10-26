# Patch Strata+ (solo locali — mai pushate, nessuna PR)

Base: Niko1221/Strata @ 7dd5cf18e68c639a8773e096c5c79f971ea2a9f5. Generate con `git diff` dal worktree locale
`/workspace/strata-policy/patchwork` (branch locale `strataplus-policy-local`, remote di push disabilitato).

Ordine di applicazione (ognuna è il diff rispetto alla precedente): **P2 → P3 → P4 → P1 → P5 → P6**.
In alternativa `ALL_P1-P6_cumulative.diff` (fino a P6) o `ALL_P1-P5_cumulative.diff` (fino a P5) (verificato con `git apply --check` su 7dd5cf18 pulito).

| Patch | Cosa | Env | Stato |
|---|---|---|---|
| P2_deterministic_cost.diff | `DraftPolicy::set_frozen_costs`: costi = tabella seminata (STRATA_SPEC_COST_TABLE), non appresi | `STRATA_SPEC_COST_FROZEN=1` | draft_policy compilato + test ✔; hook generate.cpp non compilato |
| P3_counterfactual_feedback.diff | `DraftPolicy::observe_counterfactual`: il braccio non giocato è valutato sui token committati (censurato a a+1) | `STRATA_SPEC_CF=1` | compilato + test ✔; hook generate.cpp non compilato |
| P4_pool_source.diff | `PoolSource` (pool persistente cross-request, eviction a metà, gate di match), `register_pool_from_env()` via `extra_draft_sources()`, offerto anche al braccio lookup principale | `STRATA_LOOKUP_POOL=<cap>[,<gate>]` (es. `1048576,12`) | compilato + `pool_source_test` ✔; hook generate.cpp non compilato |
| P1_trace_jsonl.diff | traccia `strataplus.v1` JSONL dal serve loop (request / round / request_end) | `STRATA_PLUS_TRACE=<path>` | non compilato (generate.cpp richiede header CUDA) |
| P5_joint_gate.diff | `JointGate`: gate unico sorgente+profondità (candidato principale H1+H4), variante entropy stop | (wiring proposto: `STRATA_SPEC_JOINT=1`, docs/strataplus_joint_gate.md) | compilato + `joint_gate_test` ✔; parità col replay (`tests/test_joint_gate_parity.py` PASS, dopo la correzione CostRLS); wiring nel motore = solo design |

Test compilati con `zig c++ -std=c++20` (suffix_drafter_test, controller_test, draft_policy_test, pool_source_test,
joint_gate_test: tutti PASS). `src/program/generate.cpp` NON è stato compilato (dipende da cuda_runtime.h): gli hook
P1–P4 lì dentro sono bozze verificate solo per scope delle variabili, da compilare sul vostro build.

La libreria del replay `replay/native/libstrata_spec_capi_p3.so` è costruita da questi sorgenti patchati
(`strata_spec_capi_p3.cpp`: dp_observe_counterfactual, dp_set_frozen_costs, jg_*).

## Correzione CostRLS in P5 (25/10/2026)

Il modello di costo online di `JointGate` (e del gemello Python `CostRLS`) aveva un difetto di esplorazione: la clamp
monotona in T veniva applicata anche alle righe già misurate, così la riga T=2 restava incollata a una riga T=1 non ancora
appresa (prior scalato dal primo campione) e veniva sovrastimata in modo permanente (2.36 vs 1.81 in unità di step, P1),
poi mai più provata. Correzione: clamp solo per righe con < 3 campioni; righe poco provate limitate dall'interpolazione
lineare dei vicini misurati (ottimismo → vengono provate e corrette); costi per token draft/lookup ≥ 0.
Diagnosi fatta sul seed sintetico riportato (code|P1, seed 7): è una correzione di bug, ma va dichiarata come
sviluppo fatto guardando quei dati. Risultati prima della correzione conservati in `replay/results/v2/*_pre_costfix/`.

## PATCH FINALE LOCALE — braccio A (decisione Strata Lead, 25/10/2026)

Commit locale **2962494a908dde1f73a7a976e22a7a0a38acee9d** sul branch `strataplus-policy-local`, figlio di
051326aa2931e04a9fbdd226f6592cf66e53516e (nessuna riscrittura della storia, nessuna push, nessuna PR).
Con `STRATA_SPEC_JOINT=1` il gate è `JointGate` con `JointGate::Options()` = **braccio A**: tmax=5 (T≤5, d≤4),
skip=true (lookup-first), solo prompt lookup, nessun conf_stop, **nessun decadimento degli hazard**
(parametri di replay/frozen_params_v3.json, sha256 37bf1996…, non modificato). `JointGate::enabled_from_env()` legge la
variabile. Senza variabile: DraftPolicy come upstream 7dd5cf18 (gli hook P1–P4 restano dietro le rispettive variabili).

| File | sha256 |
|---|---|
| P5_joint_gate.diff (8d4e25b..2962494) | f9c9505cf267cbfabedd44a4e62645b810b16927041d60616415a739d42e5e03 |
| ALL_P1-P5_cumulative.diff (7dd5cf18..2962494) | de55adb02cb2f461000e35febc2d5e1d73bb88585132345f4e75386fb04d6672 |
| precedenti (051326a) in archive_051326a/ | P5 cfecef8c…, cumulativo aed3c0b1… |

Verifiche: `git apply --check` + apply su 7dd5cf18 pulito (export `git archive`) sia del cumulativo sia della sequenza
P2→P3→P4→P1→P5: entrambi OK, alberi identici fra loro e al worktree del commit.
Test (g++ 14.2 con `-fsanitize=address,undefined -fno-sanitize-recover=all`, e zig c++ senza sanitizer): suffix_drafter,
controller, draft_policy, pool_source, joint_gate (+ nuovo blocco "defaults = braccio A, tmax=5", finestre ≤5, env
STRATA_SPEC_JOINT), spec_start → tutti PASS, 0 errori ASan/UBSan. Il primo test di joint_gate (profondità fino a 7
draft) ora fissa esplicitamente tmax=8, dato che il default è diventato 5.
Nota: le esecuzioni "ASan" precedenti con zig c++ non instrumentavano ASan (zig collega solo UBSan; verificato con un
overflow di heap non rilevato); da questo commit ASan è verificato con g++.
Parità C++ default ↔ replay GateV2(tmax=5, skip=True): `replay/tests/test_arm_a_default_parity.py` con
`replay/native/libstrata_spec_capi_p5a.so` (costruita da 2962494, entry `jg_new_default()` = `JointGate()`):
tune tf_d7 108 configurazioni (3 domini × P1/P2/P4 × 5 ρ fascia + 0,26 × costo V1/V2) 44.552 round + sintetiche 20
configurazioni 19.544 round: 0 differenze, T max 5. Nessuna ritaratura, holdout non usato.
`tests/test_joint_gate_parity.py` (60 configurazioni con parametri espliciti) PASS anche sulla nuova lib.

### LIMITI (da dichiarare con ogni uso)
- Vale **solo per la sequenza singola** (CLI e loop GEN di `--serve`). `batch_step`/BGEN **non usa DraftPolicy**: nessun
  effetto, e nessuna affermazione, per il serving con parallel > 1.
- I tok/s sono **stimati dal replay su proxy CPU (Qwen3.5-2B Q4_K_M)**, **non misure AMD**.
- Holdout v1.1: **contro il default** guadagno in tutti e tre i domini nella fascia ρ 0,06–0,15; **contro k=3** nessuna
  cella peggiore.
- **Contro STRATA_SPEC_COST=1, in chat nessun guadagno** e una cella nettamente peggiore (chat, P1, ρ 0,0791:
  −1,4% [−2,8; −0,2]). Coincide con l'H4(a) NO-GO; P1 è un profilo di costo **stimato dal codice, non misurato**.
- L'**holdout v1.1 è usato**: ogni confronto futuro richiede un **holdout nuovo**.
- Il wiring di JointGate in `src/program/generate.cpp` resta un **design** (docs/strataplus_joint_gate.md): non scritto né
  compilato qui (generate.cpp richiede gli header CUDA). Oggi `STRATA_SPEC_JOINT=1` è letto da
  `JointGate::enabled_from_env()` ma nessun loop del motore lo chiama ancora.


## P6 — aggancio di JointGate nel motore (decisione Strata Lead, 25/10/2026; locale, niente push/PR)

| File | sha256 |
|---|---|
| P6_engine_hook.diff (2962494..e467f6e: 079ecdd generate.cpp +116/−0, e467f6e docs) | 912b24fe6a02c4ad105f78eac6eec38a6798680fd705a243d34b25ff77f47aaa |
| ALL_P1-P6_cumulative.diff (7dd5cf18..e467f6e) | 14d4e2bb30a54c2fd5a4b9b3e9a68c5aef10ba8d8f9b95a628ddf3205a1e6fd1 |
| ALL_P1-P5_cumulative.diff (invariato, fino a 2962494) | de55adb02cb2f461000e35febc2d5e1d73bb88585132345f4e75386fb04d6672 |

Applicazione su 7dd5cf18: cumulativo e sequenza P2→P3→P4→P1→P5→P6 OK, alberi identici fra loro e al commit e467f6e.
Solo sequenza singola (CLI + loop GEN seriale di --serve), dietro STRATA_SPEC_JOINT=1; in generate.cpp solo righe aggiunte.
Sintassi (script di Scout /workspace/rocm-hdr): check_hip.sh clang++-17, g++, check_cuda.sh → exit 0; controllo negativo
→ exit 1. **Sintassi OK su HIP 5.7.1 e CUDA, link e ramo HIP≥7 non verificati.** I sorgenti della libreria non cambiano
rispetto a 2962494 (6 test PASS lì, zig + g++ ASan/UBSan); non rilanciati per non sovrapporsi alle misure di Bench.
LIMITI P6: draft MTP ancora fatto a ogni round (nessun risparmio di tempo di draft); profondità ≤ S_mtp−1 dell'engine;
niente costi congelati/seed; --lookup-chain e STRATA_SPEC_T_CYCLE disattivano il gate; la trace P1 mantiene i campi DraftPolicy.
Su CPU il greedy dipende dalla forma del batch (Specu): in check_v12 controllare la divergenza delle traiettorie prima di
attribuire al gate uno scarto di AL oltre il 2%.
