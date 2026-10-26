# Protocollo AMD v2 (Strata+ / Strata 7dd5cf18) — da eseguire sulla macchina AMD
Versione 2, 26/10/2026, ore CET. La v1 (traces/AMD_PROTOCOL.md, sha256 f1cba882fe085c2da3a24c85b7e8358e6b08462b9a447ee5fee6142212179e1c) **non è modificata**.
Le sez. 0–12 della v1 restano valide; questa v2 **prevale dove diverge**. Le sezioni A–I sono lo stato fissato a oggi.

> **Il box non ha GPU AMD. Non esiste oggi nessun numero s(T) misurato su AMD.** I valori di questo documento sono soglie
> pre-registrate o costanti di codice. I numeri CPU del repo sono **proxy CPU, non AMD** e non si trasferiscono.

## A. Ordine
1. **E-AMD-0**: larghezza della finestra (v1 sez. 1), live A/B tok/s, bracci default `--spec 4` / `--spec 8 --mtp-max-t 4` / `--spec 6`.
2. **P4 su AMD** nella stessa sessione:
   - T 1..8 con il binario Strata reale (7dd5cf1);
   - T 9..17 solo come profilo indicativo llama.cpp, marcato `"non kernel Strata"`, mai usato per decisioni.
3. **Gate** (sez. C), poi la **misura s(12)** (sez. D), poi la **regola H-LW** (sez. B).
4. Facoltativo, dopo E-AMD-0: il **braccio H-FC** (sez. I).

## B. Regola H-LW (Lead; soglie di Policy)
Fonte: strata-policy/replay/results/v2/breakeven_dsecond/ADDENDUM_regola_HLW.md, sha256 abc3ad9f6019bd9b5c13ac0c391cae28cb7debb11f805d83f2ab5e19b9312a1b (riverificato su disco il 26/10 CET).
- **Se vince (a′) `--spec 8 --mtp-max-t 4`:** GO se **s(12)/s(8) ≤ 1.3645 in code OPPURE ≤ 1.3306 in edit**.
- **Se vince il default (a) `--spec 4` (S=6):** GO se **s(12)/s(6) ≤ 1.7813 in code OPPURE ≤ 1.7114 in edit**.
- **Rapporto** = s(12) del **binario patchato** / s(8) oppure s(6) del **binario installato 7dd5cf1**.
  - I due binari girano in processi separati, alternati a blocchi ABAB nella stessa sessione e sulla stessa macchina.
  - Installato: `STRATA_SPEC_T_CYCLE=6,8`. Patchato: `STRATA_SPEC_T_CYCLE=6,8,12`.
  - Stessi file oracolo, prompt e seed.
- Se vince `--spec 6`: nessuna soglia è fissata. Chiedere al Lead.
- **Il GO autorizza solo la patch completa**, con kShape riempita dal profilo s(T) misurato su AMD.
- **Verdetto finale** = A/B live tok/s su AMD, con lo stesso criterio di E-AMD-0: CI95 > 0 in code o edit e nessuna cella W.

## C. Binario di misura congelato e GATE obbligatorio
**Binario (verificato su disco il 26/10):**
- commit `e441f3a` ("STRATA+ P-T12 measure v3: self-check STRATA_HC_PERSIST a T <= 8 (C7), parity s2 grouped con max_group = 8");
- branch `strataplus-pt12-measure`, worktree /workspace/strata-policy/pt12_worktree;
- catena dei commit: e441f3a → d6d4358 → b557725 → 7dd5cf1.

**File della patch (in /workspace/strata-policy/patches/):**
| file | sha256 |
|---|---|
| P_T12_MEASURE_v3.md | 338c747aae53165f3204d6236f7874ba7ca272b7fa5b1f36e78e3d1e0d66f8b1 |
| P_T12_measure_v3.diff | 599b6a6fbc2a2c6b97343c47b06c15f336e25cdc01dd1d0de5d015ed716a636b (uguale a `git diff 7dd5cf1..e441f3a`, verificato) |
| P_T12_v3_delta.diff | df69b99a63cc8193ba3e779a060a02a8b28e06170d0dac373a204a927ba1593a |

**Revisioni Scout** (scout_patch_support.md: il file cresce, quindi lo sha citato è quello della versione indicata):
- §10.C: 98de5f768de0400757d14da2574250dc49daaa89e753c114b12f4cfd2985d449
- §10.D: b647e52d1412f836545cb7a70512560f13a9970784bec573786ab058582c40ac

**Hash del binario compilato:** da registrare quando viene compilato sulla macchina AMD. Oggi non esiste.

**GATE: devono passare tutti e quattro i punti prima di leggere qualunque tempo s(12). Se uno fallisce, nessun rapporto si legge** e i tempi T=12 raccolti restano marcati "non letti".
- **(a) Parity harness**, `src/kernels/s2_expert_grouped_parity.cpp`, caso **4b** (L427-445 in e441f3a):
  - `moe_grouped_s2` con `max_group=8`, confrontato bit a bit con la corsa `max_group=0`;
  - richiesto **g_fail = 0**;
  - **mai eseguito finora.**
- **(b) Registri e occupancy** delle istanze `<8>` uguali a 7dd5cf1, letti dall'output di build (resource usage per kernel).
- **(c) Parità greedy:**
  - **P1**: patchato vs installato alla stessa T, per T 1..8, deve essere **bit-identico**;
  - **P2**: patchato a T=9 e T=12 vs patchato a T=1. Il tasso di identità si confronta con quello di installato T=8 vs T=1. T=9 entra solo in un ciclo di sola parità.
- **(d) Regressione** di s(T ≤ 8), patchato vs installato, a coppie alternate: deve restare entro **±1%**. Ogni eccesso si registra come costo della patch ed entra nel verdetto.

## D. Condizioni di misura s(12)
1. **Env:** non impostare `STRATA_HC_PERSIST`, `STRATA_GR_V3`, `STRATA_GR_SPLIT` né `STRATA_HC_Q8` (con T > 8 la patch esce con exit(1)).
   - Registrare l'**env completo di ogni run** da `/proc/<pid>/environ`.
   - Un segnale di persist attivo in stderr rende la sessione non valida.
2. **Percorso:** `--spec 12 --suffix-draft 0 --spec-oracle <file>`, con `STRATA_SPEC_T_CYCLE=6,8,12` sul patchato e `6,8` sull'installato, più `STRATA_VERIFY_PROFILE=1`.
   - Leggere la riga `window cost (ms/round)` (generate.cpp L16761 in e441f3a; L16747 in 7dd5cf1).
3. **Solo CLI**, mai `--serve` (nel patchato la guardia esce con codice 2). Non eseguire expert_multi_test su questo build.
4. **Fallback OOM a 11 righe:** se in stderr compare `not enough VRAM left for a %d-token verify window` (generate.cpp **L16622-16627** in e441f3a; fprintf a L16625), la sessione è non valida per s(12).
5. **Primo round di ogni T escluso:** lo fa già il codice (`t_cycle_seen[T]++ > 0`). Nessuna esclusione manuale in più.

## E. Conteggio dei miss
- **Per T (patch):** riga `window CPU miss/round (sum over all layers; …)`, nella forma `T12:x(ent=..,rmiss=..,rnomiss=..)` (L16766-16769 in e441f3a).
  - È una **somma per round su tutti i layer**: ent = voci (token, expert) servite dalla CPU; rmiss/rnomiss = round con e senza miss.
- **Riga storica:** `wait for rings … CPU experts %.2f` (L16784 in e441f3a, L16762 in 7dd5cf1) è **per layer**, quindi ha un'altra scala. Non mescolare le due.
- Riportare s(12)/s(8) e s(12)/s(6) separati per i round con 0 miss e con più di 0, oltre al valore complessivo.

## F. Split, controllo MTP e fallback generici
- **Split CPU:** sul percorso expert CPU, nt > 8 viene diviso in blocchi ≤ 8. È un **bound conservativo**: s(12) può risultare sovrastimato. La patch completa userà **blocchi bilanciati** (es. 12 = 6+6).
- **Controllo MTP**, sul binario installato a T=8: s(8) con e senza `--mtp`, alternati, registrando VRAM libera e multi_misses/multi_entries.
  - Se la differenza è significativa (CI95), il rapporto senza MTP è un **bound ottimistico**.
  - In quel caso si rifà la misura con `--mtp` e `P_T12_mtp_optional.diff` (sha256 626a44edd7aad21bf9f3d28d6f9938aa2452398135ed41f8205b593e948fcf5c).
- **Fallback generici oltre 8 righe:** registrare quali percorsi sono usati:
  - lfuse/combine;
  - native_moe (`n_tok <= 8`, src/kernels/cuda/native_moe.cu:178 in 7dd5cf1, v1 sez. 8);
  - MMVQ packed q8/q6 e native_mmvq_pair/il.
  - Un NO-GO vicino alla soglia dovuto ai fallback significa **"serve il kernel nativo a 12"**, non la chiusura di H-LW.

## G. Arbitro su AMD: EMA dei costi (Lead 26/10 19:30–19:32)
- Su AMD `DraftPolicy::choose` usa i costi per riga **appresi con EMA** (kCostAlpha 0.1) dai tempi reali, con seed da `spec_cost` (set_robust, generate.cpp L16447; seed L16432).
- **Non esiste un env per congelare il costo su AMD.** Si misura il motore com'è, con l'EMA.
- Le scelte di choose dipendono dai tempi reali, quindi **non ci si aspetta che coincidano** con il replay di Policy né con la run proxy (a′) (runs/live_combo_aprime_holdout.md), che usa s(T) fisso = kShape.
- Varianti di congelamento: **"plausibili, non implementate"** (Scout §11.2, sha256 e2a51166…). Non fanno parte del piano E-AMD-0 / H-LW:
  - round_ms = 0 via env;
  - un flag frozen_ nella policy;
  - sganciare il seed da spec_cost (L16432).
  - L'unico uso previsto è il braccio opzionale H-FC (sez. I).

## H. Verdetto e P4
- GO H-LW (sez. B) ⇒ solo la patch completa con kShape dal profilo misurato.
- Verdetto finale = A/B live tok/s su AMD, con CI95 > 0 (code o edit) e nessuna cella W.
- P4 su AMD:
  - T 1..8 con il binario Strata reale;
  - T 9..17 solo come profilo indicativo llama.cpp, "non kernel Strata".

## I. Braccio opzionale H-FC (= H1-det) — "s(T) fisso calibrato contro EMA"
Fuori da E-AMD-0. **Titolare: Policy.** **Specifica della patch: Scout, in un file nuovo**, ancora da scrivere; percorso e sha da registrare qui.
- **Solo su AMD e dopo E-AMD-0.** Su CPU non si misura nulla: il replay offline di Policy è solo indicativo.
- **Confronto:** EMA (motore com'è) contro s(T) congelato.
  - Congelato = un flag `frozen_` nella policy che blocca solo l'aggiornamento del costo per riga. last_ / stale() / acceptance (ok_/bad_) / mtp_tok_ continuano ad aggiornarsi.
  - Il seed va sganciato da `spec_cost` (generate.cpp L16432).
- **s(T) congelato calibrato dal profilo P4 misurato su AMD in una sessione SEPARATA da quella dell'A/B.** Registrare percorso e sha del profilo usato. Mai valori inventati.
- **Procedura:** stessa configurazione (stesso braccio vincente di E-AMD-0), coppie alternate, stesso criterio di E-AMD-0 (CI95 > 0 in code o edit, nessuna cella W).
- **Binario patch H-FC:** da fissare quando esiste (commit e sha256). Oggi non esiste e nessun hash è stato inventato.

## J. Riferimenti proxy (solo contesto, nessun numero AMD)
- Run proxy (a′) vs default (a) con arbitro copiato: runs/live_combo_aprime_holdout.md. Scritta, non lanciata.
- Arbitro: proxy/strata_arbiter_v1.hpp, sha256 85bb5341…; porta in Python proxy/strata_arbiter_v1.py, sha256 2b0e8b9a….
- Pre-check del cap MTP: traces/mtp_cap_prefix_check.json, **non al 100%**.
