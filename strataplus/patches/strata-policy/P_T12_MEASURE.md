# P-T12 measure — verify a 12 righe solo per misurare s(12)/s(8)

Patch **locale di misura**, non di produzione. Base: Strata `7dd5cf18e68c639a8773e096c5c79f971ea2a9f5` (7dd5cf1).
Ramo locale `strataplus-pt12-measure` (worktree `/workspace/strata-policy/pt12_worktree`), commit
`b557725ff7bd3e528c5aa70ab5c013a2add89475`. Separata da P6 (`strataplus-policy-local` @ e467f6e, non toccato).
Niente push, PR o remote. Niente link, build completa o run: solo controllo di sintassi.
Ogni modifica è marcata `// STRATA+ P-T12 measure`.

## Cosa misura

`--spec 12 --suffix-draft 0 --spec-oracle <file>` con `STRATA_SPEC_T_CYCLE=8,12` e `STRATA_VERIFY_PROFILE=1`:
la riga `window cost (ms/round)` (generate.cpp L16746-16749 a 7dd5cf1, ora L16755-16757) dà il costo medio del
round per T; la nuova riga `window CPU miss/round` (subito sotto) dà, sugli stessi round, i miss CPU per round.

**s(T) è il costo del solo verify, senza MTP caricato.** Con `--spec-oracle` e senza `--mtp` l'MTP non viene
caricato (generate.cpp L5455, L16143 a 7dd5cf1) e i draft vengono dall'oracolo (`use_mtp ? drafts : oracle`,
L16592). Il costo del drafter MTP a T=12 NON è in questa misura; i punti MTP sono nel diff opzionale separato
`P_T12_mtp_optional.diff` (non applicato, vedi sotto).

## Modifiche (path:riga nel commit b557725) — stato V = verificato sul codice, P = plausibile non verificato

| # | path:riga | modifica | stato |
|---|---|---|---|
| 1 | include/strata/kernels/verify_kernels.hpp:21 | `kVerifyMaxT` 8 → 12 | V |
| 2 | include/strata/kernels/cpu/expert.hpp:143 | `cpu::MAXT` 8 → 12 (MAXT*10 = 120 ≤ 128) | V |
| 3 | include/strata/core/verify.hpp:30 | `#include "strata/kernels/verify_kernels.hpp"` | V |
| 4 | include/strata/core/verify.hpp:521-522 | `prof_t_sum_`, `prof_t_win_` [9] → [kVerifyMaxT+1] | V |
| 5 | include/strata/core/verify.hpp:537 | `last_tokens_` [8] → [kVerifyMaxT] | V |
| 6 | include/strata/core/verify.hpp:548-550 | `exec_`, `exec_nr_`, `launched_`, `launched_nr_` [9] → [kVerifyMaxT+1] | V |
| 7 | include/strata/core/verify.hpp:617 | `groups_` [9] → [kVerifyMaxT+1] | V |
| 8 | src/core/verify.cpp:2358 | loop di `profile_by_t_report` fino a kVerifyMaxT | V |
| 9 | src/core/verify.cpp:2757 | `accumulate_profile`: `last_t_ <= kVerifyMaxT` | V |
| 10 | src/kernels/cuda/native_mmvq.cu:829 | `MAX_NCOLS` 8 → 12 | V |
| 11 | src/kernels/cuda/native_mmvq.cu:1519-1523 | `launch_multi`: case 9..12 + messaggio 2..12 (ramo wave gfx906 invariato) | V |
| 12 | src/kernels/cuda/native_mmvq.cu:1804 | `validate_shape`: messaggio 1..12 | V |
| 13 | src/kernels/cuda/native_mmvq.cu:2058, 2211 | `q8_packed_mmvq`/`q6_packed_mmvq`: `ncols > 8` → false (ripiego sul layout GGUF) | V |
| 14 | src/kernels/cuda/shared_expert.cu:219-220 | `shared_expert_multi`: limite 8 → 12 | V |
| 15 | src/kernels/cuda/native_bf16.cu:298-300 | `bf16_gemv_fp32_mmvf_multi`: limite 8 → 12 | V |
| 16 | src/kernels/cuda/native_bf16.cu:303 | `STRATA_MMVF_ROWS` (launch_rows, NT ≤ 8) solo con n_tok ≤ 8 | V |
| 17 | src/kernels/cuda/native_bf16.cu:328-329 | macro STRATA_MMVF_M: `case 9..12` → `<N, 12, false>`; default `<N, 8, false>` invariato | V |
| 18 | src/kernels/cuda/s2_expert_grouped.cu:826 | `GMAX` 8 → 12 (static_assert `GMAX >= kVerifyMaxT` passa) | V |
| 19 | include/strata/kernels/fused_gr.hpp:68 | `kFusedGrMaxT` 8 → 12 (obbligatorio) | V |
| 20 | src/kernels/cuda/fused_gr.cu:217 | `static_assert(sizeof(GrMulti) <= 4096)` (parametro per valore) | V (passa in sintassi HIP e CUDA) |
| 21 | src/kernels/cuda/fused_gr.cu:2180-2183 | `launch_q8`: `case 8` esplicito; `default` = fprintf + exit(1) (prima troncava a <8>) | V |
| 22 | src/kernels/cpu/pool.cpp:1320-1346 | `pt12_split_over8`: job con nt > 8 → job da ≤ 8 token consecutivi | V (indipendenza per riga, vedi sotto) |
| 23 | src/kernels/cpu/pool.cpp:1349-1352 | `run_split_multi`: split e ricorsione | V |
| 24 | src/kernels/cpu/pool.cpp:1392-1395 | `run_split_multi_native`: split e ricorsione | V |
| 25 | src/prefill/prefill.cpp:3860 | `c <= cpu::MAXT` → `c <= 8` (il prefill resta a 8) | V |
| 26 | src/program/generate.cpp:16408-16410 | vettori per T: `t_cycle_miss`, `t_cycle_ent`, `t_cycle_rmiss` | V |
| 27 | src/program/generate.cpp:16612 | lettura di `multi_misses`/`multi_entries` subito prima di `ver.run` | V |
| 28 | src/program/generate.cpp:16716-16719 | accumulo nello stesso blocco di `t_cycle_ms` (stessa condizione, primo round di cattura escluso) | V |
| 29 | src/program/generate.cpp:16759-16765 | stampa `window CPU miss/round` | V |

File toccati (righe +/−): verify.hpp 8/7, cpu/expert.hpp 1/1, fused_gr.hpp 1/1, verify_kernels.hpp 1/1,
verify.cpp 2/2, pool.cpp 35/0, fused_gr.cu 5/1, native_bf16.cu 5/3, native_mmvq.cu 9/3, s2_expert_grouped.cu 1/1,
shared_expert.cu 2/2, prefill.cpp 1/1, generate.cpp 15/0. Totale 13 file, 86 aggiunte, 23 rimozioni.

## Evidenze

**fused_gr (obbligatorio).** verify.cpp riempie `FusedGrArgs fa[kFusedGrMaxT]` per t < T: con T = 12 servono 12
posti. fused_gr.cu: tile 1280 su gfx1100 (L1079-1084, `small_tile = true` sotto `__HIPCC__` senza GFX906),
`want = kFusedGrMaxT * tv * sizeof(float)` = 12 × 1280 × 4 = 61 440 B (60 KiB) contro 64 KiB di LDS, troncato
a `optin` se più grande (L1093-1094). Margine di occupancy plausibile, **non verificato** (nessun run).
`GrMulti` passato per valore: static_assert ≤ 4096 B aggiunto e passato.

**kMaxT / clamp dell'oracolo.** `DraftPolicy policy(o.spec)` (generate.cpp L16429) clampa a 8
(draft_policy.cpp L30) e `observe` clampa t (draft_policy.cpp L155): innocuo per la misura, la larghezza viene
da `STRATA_SPEC_T_CYCLE` (L16389-16397, T dal ciclo L16553). `ver.init(..., o.spec)` (L16139) dimensiona i buffer
del verify con max_t = 12 (verify.cpp L871-872 `native_q8_1_bytes(max_in, T)`, da qui MAX_NCOLS ≥ 12).
DraftPolicy e draft_policy.cpp esclusi dalla patch.

**Percorso CPU dei miss.** voci kind −1 in `expert_pool_dispatch_multi` → `drive_pool_multi` (generate.cpp
L1159-1165) → `run_split_multi` / `run_split_multi_native` (expert_source.cpp L5133-5134, L5178-5179); il prefill
chiama `run_split_multi_native` (prefill.cpp L4048) ma con c ≤ 8 (riga 25). `ExpertJobMulti` ha
`act/out/nact[MAXT]` (pool.hpp L59-65): con MAXT = 12 i job a 12 token ci stanno.

**Split nt > 8 (riga 22-24): indipendenza per riga.** Ogni token t di un job ha input propri (`act[t]` /
`nact[t]`) e output propri (`out[t]`, "H floats, written by exactly one worker", pool.hpp); i kernel scrivono
`ff[t][r] = …` e `out[t][r] = o[t]` per assegnazione, non accumulo (expert.cpp, `s2_expert_*_rows_multi`;
native_expert.cpp `ff[t][r] = …`); il peso del router lo applica l'host dopo. Lo scratch è per job
(`split_multi_[e].ff[t]`, `.a2[t]`, `.hq[t]`, pool.hpp), e i sotto-job hanno indici e distinti; il buffer
`thread_local gbuf/ubuf[MAXT][FF]` del ramo Q2 è indicizzato per t. Nessuno stato per riga o accumulo dipendente
dal blocco. Il sotto-vettore vive fino al ritorno della chiamata ricorsiva (`mjobs_` punta lì solo durante la
chiamata). Effetti: il blob dell'expert viene letto una volta per blocco (8+4 a T = 12) → costo dei miss a T > 8
**al più sovrastimato**; `multi_bytes` conta i sotto-job (statistica). Con più di `kMaxSplitMulti` sotto-job
`run_split_multi` passa al percorso un-token-per-volta già esistente (esatto). **Plausibile, non verificato:** un
blocco di 1 token (T = 9 → 8+1) può prendere il kernel a token singolo di native_expert.cpp (`exact_one` /
`mt_min`, L262-380), con arrotondamento eventualmente diverso dal multi; non cambia la natura della misura.
Nessuna guardia di abort resta in native_expert.cpp né in expert.cpp (rimosse; dopo lo split non servono).

**Contatore miss (6').** `multi_misses` = coppie (layer, expert) distinte calcolate dalla CPU (+= njobs,
expert_source.cpp L5209), `multi_entries` = voci (token, expert) servite dalla CPU (++ L5126), dichiarati
expert_source.hpp L643-644. Il delta è letto subito prima di `ver.run` (dentro `retry_round`, quindi riletto dopo
un retry per OOM; il `goto` è all'indietro) e accumulato solo dove si accumula `t_cycle_ms` (stessa condizione:
`!t_cycle.empty() && timed_round && T <= o.spec && t_cycle_seen[T]++ > 0`). Stampa:
`window CPU miss/round  T8:<miss/round>(entries=<voci/round>, rounds miss=<n> no-miss=<n>) T12:…`.

## Esclusioni (non toccati)

DraftPolicy (`kMaxT`, draft_policy.cpp), batch (`brow_/last_rows_/b_out_/last_pos_b_[8]`), PW `tok[8]`,
lookup-chain, kernel CPU nativi, MTP (diff opzionale), generate.cpp tranne il contatore, ramo wave gfx906 di
native_mmvq, split K di fused_gr su gfx906. Statistiche di route (`rs_win_[9]`, `rs_dev_`, verify.cpp L1982,
L2388, L2742) restano a 8: `STRATA_ROUTE_STATS` non riporta T > 8 (deviazione voluta, solo diagnostica).

## Rischi

- Smem fused_gr 61 440 B su 64 KiB (gfx1100): occupancy non verificata.
- OOM alla cattura del grafo T = 12: il codice riduce `win_cap` a 11 (generate.cpp L16612-16617 a 7dd5cf1) e lo
  stampa su stderr; in quel caso la misura T12 NON esiste: controllare stderr.
- `STRATA_HC_Q8=1` con T > 8: exit(1) voluto (riga 21). Non usarlo nella misura.
- gfx906 non supportato da questa patch (wave MMVQ throw a > 8; split K di fused_gr con 12 × GS_SL float di smem).
- CPU: split in blocchi da 8 → costo dei miss a T > 8 sovrastimato (conservativo); leggere `window CPU miss/round`
  e confrontare s(12)/s(8) a parità di miss/round, o riportarlo.
- Route stats limitate a 8; packed q8/q6 MMVQ e `native_mmvq_pair/il`, native_moe.cu L178, q8_sm60.cuh L121
  tornano false a > 8 (ripiego su kernel generici: s(12) può includere un percorso diverso da s(8)).

## Anomalie e differenze mappa ↔ codice

- `q2_0_gguf_rows_multi` / `s2_*_rows_multi` hanno default `<8>` che troncherebbe a > 8: reso irraggiungibile dallo
  split in pool.cpp.
- fused_gr `launch_q8` default `<8>`: troncava silenziosamente (riga 21).
- native_bf16: Scout suggeriva "default `<N, kVerifyMaxT>`"; applicato come `case 9..12 → <N, 12, false>` con default
  `<N, 8, false>` invariato (equivalente per 9..12, ≤ 8 bitwise come prima).
- iq_kernels.cu L1860: commento "kVerifyMaxT = 8" non aggiornato (codice generico, nessun effetto).
- RouterLookahead clamp 8 (expert_source.cpp L3048): innocuo.
- MTP (diff opzionale): oltre ai punti della mappa servono `step_exec_` e `step_exec_c_` [kVerifyMaxT+1]
  (j fino a max_t − 2 = 10: mtp.cpp L1582, L1629, L1692, L1759, L1809) e una guardia `n_out > 8` in `chain_launch`
  (`ev_step_[8]`, `chain_tok_[8]`, `chain_prob_[8]`, n_out fino a max_t − 1 = 11). Inclusi nel diff opzionale e
  dichiarati come aggiunte oltre la mappa.
- La patch di misura non si applica pulita sopra P6 (e467f6e): conflitto di contesto solo in generate.cpp L16709
  (P6 aggiunge `joint->observe` subito dopo il blocco t_cycle); gli altri 12 file si applicano (`--exclude`).
  Voluto: diff separato da P6, basato su 7dd5cf1.

## Sintassi (nice -n 19, sequenziale, tempi in cpu_busy_policy.log)

- HIP 5.7.1 host (`check_hip.sh`, clang++-17): verify.cpp, pool.cpp, prefill.cpp, generate.cpp, expert_source.cpp,
  cpu/expert.cpp, mtp.cpp, native_expert.cpp → rc 0 (mtp.cpp e native_expert.cpp con gli header ggml di
  build-strata-cpu/_deps).
- CUDA host (`check_cuda.sh`, g++): stessi file → rc 0.
- HIP device (clang++-17 `-x hip --offload-arch=gfx1100 -nogpulib`): native_mmvq.cu, native_bf16.cu,
  shared_expert.cu, s2_expert_grouped.cu, fused_gr.cu, verify_kernels.cu → rc 0.
- CUDA .cu (clang++-17 `-x cuda` sm_86, header CUDA 12.9 da wheel + cccl + curand, host-only e device-only):
  native_bf16.cu, shared_expert.cu, s2_expert_grouped.cu, fused_gr.cu, verify_kernels.cu → rc 0; native_mmvq.cu → 4
  errori `__ldcs` (L1989, L1990, L2141, L2142), **identici a 7dd5cf1** (stesso controllo sul file base: stessi 4
  errori, clang vs nvcc), nessun errore nuovo. Controllo negativo (static_assert kVerifyMaxT == 8) → rc 1.
- Non verificati: nvcc reale, link, ramo HIP ≥ 7, gfx906.

## Istruzioni di misura su AMD (gfx1100)

1. `git checkout strataplus-pt12-measure` (o applicare `P_T12_measure.diff` su 7dd5cf1), build HIP abituale.
2. Run con lo stesso modello/flag della misura s(8) di riferimento, più:
   `STRATA_SPEC_T_CYCLE=8,12 STRATA_VERIFY_PROFILE=1 strata generate ... --spec 12 --suffix-draft 0 --spec-oracle <file>`
   (senza `--mtp`, senza `STRATA_HC_Q8`).
3. Controllare stderr: nessun "not enough VRAM left for a 12-token verify window" (altrimenti niente T12).
4. Leggere `window cost (ms/round)` → s(8) = T8, s(12) = T12, rapporto s(12)/s(8); `window CPU miss/round` →
   miss/round e round con/senza miss per T; `GPU stages per window width` ora fino a T12.
5. s(T) = costo del solo verify, **senza MTP caricato**.

## Diff opzionale MTP (non applicato)

`P_T12_mtp_optional.diff` (si applica sopra b557725, `git apply --check` rc 0; sintassi mtp.cpp e generate.cpp
HIP host e CUDA host rc 0 con il diff applicato temporaneamente, poi ripristinato):
mtp.hpp include verify_kernels.hpp; `step_exec_`, `round_exec_c_`, `step_exec_c_`, `prefill_exec_`,
`prefill_dev_exec_`, `round_exec_` [9] → [kVerifyMaxT+1]; mtp.cpp L396 `xq_` con `max(T, 8)` colonne;
guardia `n_out > 8` in `chain_launch`.
