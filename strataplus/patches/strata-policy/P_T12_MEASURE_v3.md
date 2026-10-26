# P-T12 measure v3 — fix C7 (persist a T ≤ 8), parity <8> e condizioni di misura

Patch **locale di misura**, non di produzione. Base 7dd5cf1 (`7dd5cf18e68c639a8773e096c5c79f971ea2a9f5`), ramo
`strataplus-pt12-measure` (worktree `/workspace/strata-policy/pt12_worktree`):
v1 `b557725` → v2 `d6d4358fc64ef9457e893f60e634c5432d38f7a9` → **v3 `e441f3a1338075889b3b96132ae86ad8688263ce`**
(nuovo commit sopra d6d4358, senza amend; niente push, PR o remote). P6 non toccato.
**Questo documento integra `P_T12_MEASURE_v2.md` (sha256 `c6806e76dd152f41def590fd59c67c386f305df4e8a48f03193f7ea837378817`)**:
tutto ciò che è scritto lì vale ancora, salvo quanto aggiunto qui. Approvazione Scout di d6d4358: §10.C di
`/workspace/strata-plus/scout_patch_support.md` (sha256 `98de5f768de0400757d14da2574250dc49daaa89e753c114b12f4cfd2985d449`).
File: `P_T12_measure_v3.diff` = `git diff 7dd5cf1 e441f3a` (misura completa: 19 file, +193/−59);
`P_T12_v3_delta.diff` = `git diff d6d4358 e441f3a` (2 file, +22/−1). Marcatore: `// STRATA+ P-T12 measure v3`.

## Modifiche v3 (path:riga in e441f3a) — V = verificato sul codice, P = plausibile non verificato

| # | path:riga | modifica | stato |
|---|---|---|---|
| C7 | src/kernels/cuda/fused_gr.cu:3022 | self-check di `fused_gr_persist_init`: `for (int T = 1; T <= kFusedGrMaxT && ok; ++T)` → `T <= kGrBaseMaxT` (8) | V |
| 4b | src/kernels/s2_expert_grouped_parity.cpp:15, 415, 425, 427-445 | caso 4b: stessi gruppi del caso 4 con `max_group = 8` | V (sintassi); **test NON eseguito** |

### C7 — dettaglio
- `kernel_t` (fused_gr.cu L2877-2888) ha `case 1..8` e restituisce `nullptr` oltre; con v1/v2 il self-check
  (L3022) arrivava a `kFusedGrMaxT` = 12 e a T = 9 avrebbe lanciato `kernel_for(9)` = nullptr (`hcp::launch`, L2902,
  chiamato dal check a L2994).
- 7dd5cf1: lo stesso loop (L2998 in 7dd5cf1) è `T <= kFusedGrMaxT` con `kFusedGrMaxT = 8` (fused_gr.hpp L68 in
  7dd5cf1) → copriva **esattamente 1..8**. Dopo il fix il loop è di nuovo 1..8 e `st.max_t` (L3043) ≤ 8 come in 7dd5cf1.
- Differenza residua (innocua): i buffer del check sono dimensionati con `TM = kFusedGrMaxT` (L2950) = 12 righe; a
  T ≤ 8 se ne usano al più 8 (memset più ampi, nessun effetto sul risultato).

### Fallback a runtime per T 9..12 con STRATA_HC_PERSIST (richiesta Scout) — **già presente, nulla toccato**
- `fused_gr_read_persist` (fused_gr.cu L3050-3062): `if (n_tok > st.max_t) return false;` a **L3056**, prima di
  `hcp::launch` (L3060). Con C7 `st.max_t` ≤ 8, quindi a T 9..12 `kernel_for`/`kernel_t` non viene mai chiamato.
- Il chiamante passa al percorso senza persist: verify.cpp **L1367**
  `if (fused_gr_read_persist(fa, n, cs)) return false;` seguito da `return fused_gr_read_multi(...)` (L1368);
  contratto in fused_gr.hpp L91-92 ("returns false when it did not run (off, too many tokens, …) - then the caller
  runs `fused_gr_read_multi`").
- Altri punti che lanciano il persist: solo `hcp::launch` (L2902, unico `kernel_for(n_tok)<<<…>>>`), chiamato dal
  self-check (L2994, ora T ≤ 8) e da `fused_gr_read_persist` (L3060, dietro la guardia L3056);
  `hc_persist_parity.cpp` L85/L113 cicla con `TM = 8` (L26). Senza C7 il fallback NON bastava: il crash era nel
  self-check, non nel dispatch.

### 4b — parity delle istanze <8> (C3)
Fino a v2 le istanze `GM = 8` non avevano test (l'harness passa `max_group = 0` → GMAX 12). v3 aggiunge, nel caso 4
(T = 8, gruppi di 1..8 voci da `sizes[]`, un gruppo su blob host mappato, capacità > gruppi), per fp32 scales e fp16 d:
1. `twice(...)`: vecchi vs nuovi kernel bitwise con `moe_grouped_s2(..., /*max_group=*/8)` (stessi controlli di path);
2. `reference(...)`: lo stesso riferimento host in doppia precisione del caso 4;
3. confronto bitwise (out + scratch) contro la run `max_group = 0` degli stessi input (`r_g0`, L415/L425); differenza
   → `++g_fail`.
**Il test non è stato eseguito** (nessuna GPU/build): solo sintassi. Che <8> e <12> siano bitwise identici è **P**
(stesso ordine di somma per voce; cambiano solo dimensioni e stride della smem): se non lo fossero il caso 4b fallisce
e lo dice. Registri e occupancy delle <8> restano **non verificati fino alla build**.

## Condizione (1) di misura
Si misura **senza** `STRATA_HC_PERSIST`, `STRATA_GR_V3`, `STRATA_GR_SPLIT` e `STRATA_HC_Q8`, anche dopo C7 (C8):
- GR_V3 (opt-in, fused_gr.cu L2262-2318; in particolare L2270-2271 `need1 = kFusedGrMaxT * N * 4` e L2318 default
  `gr_up_v3_kernel<1, kFusedGrMaxT, false>`) resta a 12 righe anche a T ≤ 8;
- GR_SPLIT (gfx906, opt-in, L2327-2348): `gr_down_split_kernel` con `acc[kFusedGrMaxT]` (L1580) e
  `gr_up_fast_kernel` / `gr_up_multi_kernel<>` default (L2341-2342) restano a 12;
- STRATA_HC_PERSIST: corretto da C7 ma tenuto fuori dalla misura; STRATA_HC_Q8: a T > 8 exit(1) voluto (v1, L2201-2202).

## Regola del Lead (ordine di lettura)
1. **Prima** dei tempi di s(12): parità **P1 e P2** sulle istanze <8> (es. `s2_expert_grouped_parity` col caso 4b, da
   eseguire sulla build) **e** confronto di s(T ≤ 8) fra patchato e 7dd5cf1 (stessa sessione, binari alternati).
2. Se uno dei due fallisce **non si legge nessun rapporto**.
3. Solo dopo: decisione = s(12) patchata / s(8) 7dd5cf1; ramo (a) = s(12) patchata / s(6) 7dd5cf1 (come v2).

## Due scale di miss nello stesso output
- Riga nuova `window CPU miss/round (sum over all layers; …)` (src/program/generate.cpp L16766-16769): **somma per round su tutti i
  layer**, per T.
- Riga storica `verify window … CPU experts %.2f distinct / %.2f routed per layer` (src/program/generate.cpp L16784-16789, la
  stampa con i valori è L16788-16789): **per layer** (divisa per `rounds * g.n_layers`), su tutti i round.
- Non confrontarle direttamente: la nuova ≈ storica × n_layers solo a parità di insieme di round.

## Sintassi (nice -n 19, taskset -c 0, sequenziale, nessun download; righe in cpu_busy_policy.log)
- fused_gr.cu: HIP device gfx1100 (clang++-17 `-x hip -nogpulib`) rc 0; CUDA sm_86 (clang++-17 `-x cuda`, header
  cudaroot) host-only rc 0, device-only rc 0. Nessun errore, quindi nessun confronto con la base necessario (in v2 lo
  stesso file era già rc 0 in tutte e tre).
- s2_expert_grouped_parity.cpp: HIP host (`check_hip.sh`) rc 0, CUDA host (`check_cuda.sh`) rc 0.

## Diff opzionale MTP (non applicato, non modificato)
`git apply --check P_T12_mtp_optional.diff` su e441f3a → rc 0 (mtp.hpp, mtp.cpp).
