# Holdout v1.1 — rivalutazione "draft pieno" (POST-HOC)

**Etichetta:** rivalutazione post-hoc dell'holdout v1.1 GIÀ USATO, per correggere il modello di costo (con P6 il motore calcola il draft MTP pieno a ogni round). **NON è una nuova validazione.** Conto solo descrittivo: nessuna regola di decisione applicata, la scelta A/B NON viene riaperta (Strata Lead, 04:48 CET). Nessun tune, nessun check_v12. tok/s **STIMATI** (replay; profili P1/P2 stime da codice, P4 proxy CPU Qwen3.5-2B Q4_K_M, non AMD).

- Script: `replay/holdout_v11_fulldraft.py` (nuovo; NON scrive run_holdout_v11_opened.json). Output: `holdout_v11_fulldraft.json`, `summary_band.json`, `run_stdout.txt`, `run_time.txt`.
- Parametri congelati: frozen_params_v3.json invariato (sha256 registrato nel JSON). Stesse celle (dominio × P1/P2/P4 × ρ {0,059…0,1394} + 0,26 di controllo × V1/V2), stesso boot_ratio (cluster sulle sessioni, B=2000, seed 0). Il "PRIMA" è letto da `results/v2/holdout_v11/holdout_v11.json`; i baseline ricalcolati coincidono al bit (diff tok/s = 0).
- CPU: 04:50:07–04:50:29 CET, 22 s user, `nice -n 19`, 1 processo (registrato in cpu_busy_policy.log). Sotto la soglia di 2 CPU-minuti.

## (a) Il simulatore contava il risparmio di draft? SÌ — nel ramo additivo, NON tramite cost_T_d

- `strata_sim/sim2.py` L22–23: `Profile.cost(T, d_mtp, k_lu) = s[T-1] + rho_mtp*d_mtp + rho_lu*k_lu`.
- `sim2.py` L90–93 (`walk`): `src, T, d, klu = policy.act(...)` → `c = prof.cost(T, d, klu)`: si addebita la **d scelta dalla policy**; `policy.update(..., c)` (L100) fa imparare al gate quel costo.
- `GateV2.act` (sim2.py L463–466 rem≤0/no MTP → d=0; L470–471 skip → `return ..., 0, klu`; L473–501 d = draft effettivamente svolti fino allo stop del value-test, anche se poi vince lookup/none). Quindi skip e d bassa = risparmio di draft.
- `cost_T_d` **non è mai letto dal replay** (grep vuoto in strata_sim/ e replay/*.py; anche la `derivation` di cost_p4_cpu_099ceda_s8lin.json lo dichiara: "cost_T_d, cost_by_k NON usati dal replay"). `load_p4` (sim2.py L38–59) prende solo `s` (= cost_T_d[T,0]) e `rho_lu`; in holdout_v11.py L40–42 ρ_mtp viene **sostituito** dal valore della cella (0,059…0,26), il rho_mtp del file (0,2695) non entra.
- Baseline nel replay: default `T, kd = S_mtp, S_mtp-1` (L181) = d=3 a ogni round, anche nei round lookup (L192; docstring L163–166); STRATA_SPEC_COST=1 `T, kd = mtp_chain_rows(...)` (L179) con kd = passi di catena svolti (native/strata_spec_capi_p3.cpp L24–31, `*steps = n`); k=3 `("mtp", 4, 3, 0)` (L158–159).
- Motore @7dd5cf18 (`git show 7dd5cf18:src/program/generate.cpp`, sola lettura): serve L11173 `S_mtp = mtp_max_t>0 ? min(mtp_max_t,S) : S`; L11174/11176 `mtp.set_max_drafts(S_mtp-1)`; L15168–15169 `mtp.draft(T, …)` a fine di OGNI round (salta solo a eos/max_new); `mtp.cpp` L1580 `max_steps = min(max_t_-1, max_drafts_)` e L1623–1657 catena intera quando min_p≤0 e nessuna chain rule; L1689 con chain rule si ferma quando `keep_draft` è falso. La chain rule è installata solo con STRATA_SPEC_COST=1 (generate.cpp L11179–11188; CLI L16426, L16449–16452, draft_next L16529/L16693). Il `T` passato a `draft` è solo il catch-up (mtp_process(T)) — mtp.hpp L101–106.
- Conclusione: default (d=S_mtp−1=3) e k=3 (d=3) e SPEC_COST (d=passi di catena) sono **già fedeli al motore** nel replay; **A e B no**: il replay addebitava ad A in media 1,2 (code) / 2,38 (chat) / 1,16 (edit) draft/round (cella P4 ρ=0,0992), mentre col P6 il motore ne calcola sempre S_mtp−1.

## Regola "draft pieno" applicata
- d addebitata = draft che il motore calcola: A tmax=5 ⇒ S_mtp=5 ⇒ **d=4 ogni round**; B tmax=8 ⇒ S_mtp=8 ⇒ **d=7**; baseline invariati (già fedeli). Le decisioni di A/B restano quelle della policy congelata; il gate osserva il costo pieno (come l'observe di P6 sul tempo misurato).
- Nota sulla formula: la Lead scrive "d = S_mtp"; il codice calcola S_mtp−1 draft (mtp.cpp L1580 + generate.cpp L11174), coerente col default del replay (kd = S_mtp−1). Ho usato S_mtp−1; con d = S_mtp il peggioramento sarebbe ulteriore (+1 ρ per round), non calcolato.
- V1 e V2 per A coincidono: differiscono solo in s(8) e A non usa mai T>5.
- Griglia P4 cost_T_d: tabella a parte, solo come controllo (ρ effettivo per draft ≈0,27–0,32, gonfiato dal lm_head a vocabolario pieno).
