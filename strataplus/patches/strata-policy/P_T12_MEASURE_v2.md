# P-T12 measure v2 — verify a 12 righe solo per misurare s(12), con T ≤ 8 identico a 7dd5cf1

Patch **locale di misura**, non di produzione. Base: Strata `7dd5cf18e68c639a8773e096c5c79f971ea2a9f5` (7dd5cf1).
Ramo locale `strataplus-pt12-measure` (worktree `/workspace/strata-policy/pt12_worktree`): v1 = `b557725ff7bd3e528c5aa70ab5c013a2add89475`,
**v2 = `d6d4358fc64ef9457e893f60e634c5432d38f7a9`** (nuovo commit sopra b557725, senza amend). Separata da P6
(`strataplus-policy-local` @ e467f6e, non toccato). Niente push, PR o remote. Niente link, build completa o run:
solo controllo di sintassi. Le modifiche nuove sono marcate `// STRATA+ P-T12 measure v2`.
File: `P_T12_measure_v2.diff` = `git diff 7dd5cf1 d6d4358` (misura completa); `P_T12_v2_delta.diff` =
`git diff b557725 d6d4358` (solo v2). I file v1 (`P_T12_measure.diff`, `P_T12_MEASURE.md`, `P_T12_mtp_optional.diff`)
restano invariati e valgono per b557725.

## Cosa misura

`--spec 12 --suffix-draft 0 --spec-oracle <file>` con `STRATA_SPEC_T_CYCLE=6,8,12` e `STRATA_VERIFY_PROFILE=1`,
**solo CLI** (`--serve` è rifiutato da questa build, vedi riga V9). La riga `window cost (ms/round)` (generate.cpp
L16761 in d6d4358) dà il costo medio del round per T; la riga `window CPU miss/round` (subito sotto, L16766-16771)
dà sugli stessi round i miss CPU **per round, sommati su tutti i layer**:
`window CPU miss/round (sum over all layers; ...): T6:<miss>(ent=<voci>,rmiss=<n>,rnomiss=<n>) T8:… T12:…`
(`ent` = voci (token, expert) servite dalla CPU per round, tutti i layer; `rmiss`/`rnomiss` = round con/senza miss).

**s(T) è il costo del solo verify, senza MTP caricato** (come v1: con `--spec-oracle` e senza `--mtp` l'MTP non
viene caricato). Il diff MTP opzionale resta separato e non applicato.

### Regola di decisione (Lead)

- rapporto di decisione = **s(12) della build patchata / s(8) di 7dd5cf1**;
- ramo (a) = **s(12) patchata / s(6) di 7dd5cf1**;
- due binari (7dd5cf1 e d6d4358), **alternati nella stessa sessione**, stesso modello/flag/oracolo.
  Con v2 i T ≤ 8 della build patchata usano le stesse istanze di 7dd5cf1 (vedi V1-V5), quindi s(6)/s(8) della build
  patchata servono come controllo di coerenza contro 7dd5cf1, non come denominatore.

### Note Scout (verificate sul codice di d6d4358)

- Letterali 8 che spengono le varianti fuse oltre 8 → **s(12) conservativo** (a T = 12 prende percorsi generici):
  - verify.cpp **L1144** `lfuse_on`: `n > 1 && n <= 8` — **V** (riga esatta).
  - verify.cpp combine `hits_in_combine`: lo Scout cita **L2165, ma lì non c'è nessun 8** (L2160-2166 sono
    `copy_rows_from_mapped*`); il letterale è a **L2169-2170** (`... && native_moe_combine_enabled() && n <= 8 &&`, L2170).
    Stessa riga in 7dd5cf1 e b557725. — V con correzione di riga.
  - native_moe.cu **L178** `native_moe_combine_hits_supported`: `n_tok >= 1 && n_tok <= 8` — **V**.
  - packed: native_mmvq.cu L2058, L2211 `if (ncols > 8) return false;` (aggiunti da v1, ripiego sul layout GGUF) — V.
  - pair: native_mmvq.cu L2850 `native_mmvq_pair`: `ncols < 2 || ncols > 8` → false — V.
  - il: native_mmvq.cu L3236 `native_mmvq_il_supported`: `ncols > 8` → false — V.
- **OOM alla cattura**: se il grafo a 12 righe non entra, `win_cap = T - 1` = 11 (generate.cpp L16622-16627,
  messaggio "not enough VRAM left for a 12-token verify window" su stderr) e il report mostra **T11**, non T12:
  in quel caso la misura T12 non esiste.
- **`expert_multi_test` non va eseguito su questa build** (regola Scout; CMakeLists.txt L2227-2229. Motivo P, non
  verificato: il test usa `c::MAXT`, ora 12, direttamente sui kernel CPU `*_rows_multi`, che hanno default `<8>`;
  lo split a 8 è in pool.cpp, che il test non attraversa).
- **Conflitto con P6 solo testuale**: `git apply --cached --check` di `P_T12_measure_v2.diff` su e467f6e (indice
  temporaneo, nessun file toccato): falliscono solo gli hunk di generate.cpp, sul blocco t_cycle (contesto a L16709
  di 7dd5cf1, dove P6 aggiunge `joint->observe`); gli altri 3 hunk di generate.cpp (guardia --serve, vettori, lettura
  pre-`ver.run`) entrano con offset, e con `--exclude=src/program/generate.cpp` il resto si applica (rc 0).
  Risoluzione: l'hunk `joint->observe` di P6 va **dopo la `}` del blocco t_cycle** (cioè dopo l'accumulo P-T12).

## Modifiche nuove v2 (path:riga in d6d4358) — V = verificato sul codice, P = plausibile non verificato

| # | path:riga | modifica | stato |
|---|---|---|---|
| V1 | src/kernels/cuda/fused_gr.cu:218-221 | `constexpr int kGrBaseMaxT = 8` + static_assert ≤ kFusedGrMaxT | V |
| V2 | src/kernels/cuda/fused_gr.cu:1100-1101, 1105-1107, 1111-1113, 1129 | `down_chunk`: `want8 = 8·tv·4` (troncato a optin); `<tv,4,true>` torna a want8 (= `want` di 7dd5cf1); attributi smem per `<tv,8>` e `<tv,8,true>`; `set_staged_attr(gr_down_staged_kernel<8,false>, 8)` | V |
| V3 | src/kernels/cuda/fused_gr.cu:1316, 1321, 1324, 1329, 1332 | down staged / multi 1280 e 2560 (q8w e no): `else if (ct <= 8)` → istanza `<…, 8>` prima del default `<…, 12>` | V |
| V4 | src/kernels/cuda/fused_gr.cu:1343/1350, 1357/1364, 1368/1375, 1379/1386 | 4 switch up (q32, q8w multi, up75, multi): `case 7: case 8:` → `<8, false[, true]>`; con `STRATA_NO_MULTI_GR` la chiave è 8 se n_tok ≤ 8 (base), 12 oltre | V |
| V5 | src/kernels/cuda/verify_kernels.cu:1056, 1106, 1151-1154 | `case 7: case 8:` → `gdn_conv_ab_kernel<8,false>`, `gdn_ab_multi_kernel<8,false>`; `gdn_state_replay_kernel<8>` a n_tok ≤ 8 | V |
| V6 | src/kernels/cuda/s2_expert_grouped.cu:853, 916, 990, 1057 | 4 kernel grouped `template <int GM = GMAX>`, GMAX → GM nei corpi (smem e clamp `ne`) | V |
| V7 | src/kernels/cuda/s2_expert_grouped.cu:1175-1181, 1191-1198, 1237-1241 | `moe_grouped_s2(..., int max_group)`: `g8 = 1 ≤ max_group ≤ 8` → istanze `<8>` (= GMAX 8 di 7dd5cf1), altrimenti GMAX 12 | V (un gruppo ha al più una voce per token: max_group = token della chiamata) |
| V8 | include/strata/kernels/s2_expert_grouped.hpp:102-103; src/core/verify.cpp:2103; src/core/mtp.cpp:1131; src/core/remote_experts.cpp:346-347 | parametro `int max_group = 0` (0 = ignoto → GMAX: harness di parità invariato); chiamanti passano `n`, `(int) T`, `(int) n_tok` | V |
| V9 | src/program/generate.cpp:2796-2802 | guardia subito dopo il parsing, prima di ogni query al device/allocazione: `if (o.serve)` → stderr «build di misura P-T12: --serve non supportato (array batch a 8), usare solo la CLI», `return 2`. Copre anche `--serve --mtp` (blocco serve L8360-~15700, incl. `dwin_s` e `t2_rej`, ora irraggiungibile) | V |
| V10 | src/program/generate.cpp:16765-16771 | stampa miss: etichetta "sum over all layers", formato `T12:1.23(ent=4.56,rmiss=10,rnomiss=30)` | V |
| V11 | include/strata/core/verify.hpp:521 | commento `(1..8)` → `(1..kVerifyMaxT)` | V |
| V12 | src/kernels/cuda/iq_kernels.cu:1860-1862 | commento: kVerifyMaxT = 12 nella build di misura (8 in 7dd5cf1), finestra a 12 righe fino a 3 passate | V |
| P1 | — | registri/occupancy delle istanze `<8>` uguali a 7dd5cf1 (stessi template e argomenti) | P (nessun ptxas/run) |

Delta v2 (b557725 → d6d4358): 10 file, 88 aggiunte, 38 rimozioni. Misura completa (7dd5cf1 → d6d4358): 18 file,
171 aggiunte, 58 rimozioni. Le righe generate.cpp della tabella v1 dopo L2795 sono spostate di +6.

## Fuori perimetro (invariati, documentati)

- fused_gr: percorso V3 (`STRATA_GR_V3`, opt-in), `gr_up_fast_kernel` (`STRATA_GR_FAST_BUILD` gfx906/CUDA, smem non
  template a kFusedGrMaxT), split K gfx906, selftest, `return kFusedGrMaxT` di `down_chunk` per dev ≥ 64.
- CPU: `cpu::MAXT` = 12 dimensiona solo array (pool.hpp, expert.hpp); nessun dispatch template per T (split a 8 da v1).
- native grouped (iq_kernels.cu): passate da GRP_NC = 4, nessun massimo di gruppo.
- Posizione citata dallo Scout per il default di `gr_down_staged`: L1304 in b557725 è il ramo `max4` (`<4>`); il
  default `<>` era a **L1305** (ora L1317).

## Sintassi (nice -n 19, taskset -c 0, sequenziale; tempi in /workspace/strata-plus/cpu_busy_policy.log)

- HIP 5.7.1 host (`check_hip.sh`, clang++-17) e CUDA host (`check_cuda.sh`, g++): verify.cpp, pool.cpp, prefill.cpp,
  generate.cpp, mtp.cpp, expert_source.cpp, cpu/expert.cpp, native_expert.cpp, remote_experts.cpp,
  s2_expert_grouped_parity.cpp → rc 0 (mtp.cpp e native_expert.cpp con `-I` agli header ggml già presenti in
  strata-bench/build-strata-cpu/_deps, come v1).
- HIP device (clang++-17 `-x hip --offload-arch=gfx1100 -nogpulib`): native_mmvq.cu, native_bf16.cu, shared_expert.cu,
  s2_expert_grouped.cu, fused_gr.cu, verify_kernels.cu → rc 0; iq_kernels.cu → 2 errori `alignas` **identici a
  b557725** (stesso controllo sul file base: L2477/L2664 → L2478/L2665, +1 riga del commento).
- CUDA .cu (clang++-17 `-x cuda` sm_86, header già presenti in rocm-hdr/cudaroot e cudawhl, host-only e device-only):
  native_bf16.cu, shared_expert.cu, s2_expert_grouped.cu, fused_gr.cu, verify_kernels.cu → rc 0; native_mmvq.cu → i
  4 errori `__ldcs` di 7dd5cf1 (L1989, L1990, L2141, L2142); iq_kernels.cu → 8 errori (7 `alignas`, 1 `#pragma
  unroll`) **identici a b557725** salvo +1 riga. Controllo negativo (static_assert kVerifyMaxT == 8) → rc 1.
- Non verificati: nvcc reale, link, run, gfx906.

## Istruzioni di misura su AMD (gfx1100)

1. Due build HIP abituali: 7dd5cf1 e `strataplus-pt12-measure` @ d6d4358 (o `P_T12_measure_v2.diff` su 7dd5cf1).
2. Stesso modello/flag/oracolo, solo CLI, senza `--mtp`, senza `STRATA_HC_Q8`, alternando i due binari nella stessa
   sessione:
   `STRATA_SPEC_T_CYCLE=6,8,12 STRATA_VERIFY_PROFILE=1 strata generate ... --spec 12 --suffix-draft 0 --spec-oracle <file>`
   (su 7dd5cf1: `--spec 8` e `STRATA_SPEC_T_CYCLE=6,8`).
3. stderr: nessun "not enough VRAM left for a 12-token verify window" (altrimenti T11, niente T12).
4. Decisione = s(12) patchata / s(8) 7dd5cf1; ramo (a) = s(12) patchata / s(6) 7dd5cf1; leggere anche
   `window CPU miss/round` per T.
5. Non eseguire `expert_multi_test` né `--serve` con questa build.

## Diff opzionale MTP (non applicato, non modificato)

`P_T12_mtp_optional.diff` (sha256 626a44ed…): `git apply --check` su d6d4358 → rc 0 (mtp.hpp, mtp.cpp).
