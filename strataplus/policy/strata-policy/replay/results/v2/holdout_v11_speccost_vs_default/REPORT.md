# Holdout v1.1 — STRATA_SPEC_COST=1 vs default installato (min_p 0,5) — RIVALUTAZIONE POST-HOC, SOLO DESCRITTIVA
Holdout già usato; nessuna regola di decisione; nessuna ritaratura; parametri congelati. **tok/s STIMATI** dal modello di costo, non misure.
**Le mtp_p vengono dal proxy llama.cpp qwen35-2b-mtp (tracce TF, dmax 7), non dal draft layer di Strata**: il taglio a p≥0,5 può essere calibrato diversamente sul motore vero.
IC95 = sim2.boot_ratio B=2000 seed 0, cluster = sessione. Script: replay/holdout_v11_speccost_vs_default.py. V1 = V2 (nessun braccio usa T=8).

## Modello fedele al motore (@7dd5cf18)
- default installato: setup.py L9420 `"--spec", "4", "--spec-min-p", "0.5"` (CLI default 0.0, generate.cpp L705).
  Catena: mtp.cpp L1689 `for (j=1; j<max_steps && (chain_rule_ ? chain_rule_(j-1,pj) : pj>=min_p); ++j)` → draft = min(3, 1+run).
  Finestra: generate.cpp L14885-14887 `else if (use_mtp && req_spec_min_p > 0.0) { T = 1; while (T < S_mtp && dprob[T-1] >= req_spec_min_p) ++T; }` → T = min(4, 1+run).
- default vecchio (min_p 0): fast path mtp.cpp L1623 `if (min_p <= 0.0f && !chain_rule_ ...)`, n = max_steps = 3 (L1657), T = S_mtp = 4.
- SPEC_COST: la chain_rule è installata solo con STRATA_SPEC_COST=1 (generate.cpp L11179-11188) e **sostituisce** il test min_p (mtp.cpp L1689; con chain_rule_ non si entra nel fast path L1623; L1708 valuta l'ultimo passo).
  La finestra è `if (use_mtp && spec_cost && !first_window) T = clamp(chain_rows,1,S_mtp)` (L14883-14884) e il ramo min_p è un `else if` (L14885): **con SPEC_COST min_p=0,5 non riduce né la catena né la finestra**.
  Unica eccezione: la prima finestra (L14889 `if (first_window) T = merge_T > 0 ? merge_T : 1;`), uguale per tutti i bracci e non modellata dal replay per nessuno.
  Quindi il braccio SPEC_COST del replay (sim2.StrataCurrent(spec_cost=True), kd = passi della catena) è già fedele anche con min_p 0,5.
- Lookup: identico in tutti i bracci (choose(T,k,match) con la T del braccio, gate su sbuf[0]==drafts[0]).

## Tabelle per dominio (banda ρ 0,06–0,15: P1/P2/P4 × 5 ρ = 15 celle; W = IC95 hi<0, B = IC95 lo>0)

#### code
| confronto | banda: mediana [min;max] | IC95 cella mediana | W/B/n banda | ρ=0,26: mediana [min;max] W/B/n | griglia P4 Δ [IC95] |
|---|---|---|---|---|---|
| spec_cost vs default_corr | +0.6% [+0.1;+3.9] | +0.6% [-0.1;+1.4] (P1|rho0.0992) | W0/B7/15 | +0.5% [-0.9;+0.5] W0/B0/3 | -0.9% [-1.8;+0.1] neutral |
| spec_cost vs default_old | +0.8% [+0.1;+1.9] | +0.8% [+0.2;+1.4] (P4|rho0.1193) | W0/B11/15 | +0.9% [+0.8;+1.6] W0/B3/3 | +0.9% [+0.2;+1.6] better |
| spec_cost vs k3 | +9.6% [+4.9;+13.1] | +9.6% [+8.1;+11.0] (P2|rho0.0992) | W0/B15/15 | +12.1% [+7.7;+13.6] W0/B3/3 | +13.7% [+11.4;+15.9] better |
| default_corr vs default_old | +0.2% [-2.7;+1.1] | +0.2% [-0.4;+0.8] (P2|rho0.0590) | W2/B3/15 | +1.1% [+0.4;+1.7] W0/B2/3 | +1.7% [+0.8;+2.7] better |

draft/round e T/round (P4 ρ=0,0992): default_old 3.00 / 4.88, default_corr 2.91 / 4.67, spec_cost 2.84 / 4.63, k3 3.00 / 3.96

#### chat
| confronto | banda: mediana [min;max] | IC95 cella mediana | W/B/n banda | ρ=0,26: mediana [min;max] W/B/n | griglia P4 Δ [IC95] |
|---|---|---|---|---|---|
| spec_cost vs default_corr | +1.7% [+1.5;+3.7] | +1.7% [+0.6;+2.8] (P4|rho0.0590) | W0/B15/15 | +2.2% [+1.9;+3.8] W0/B3/3 | +2.0% [+0.6;+3.4] better |
| spec_cost vs default_old | +10.2% [+7.6;+25.4] | +10.2% [+7.1;+13.4] (P2|rho0.1193) | W0/B15/15 | +11.8% [+9.6;+24.5] W0/B3/3 | +9.6% [+6.0;+13.1] better |
| spec_cost vs k3 | +10.6% [+8.0;+25.6] | +10.6% [+7.0;+14.2] (P2|rho0.1193) | W0/B15/15 | +12.3% [+10.1;+24.9] W0/B3/3 | +10.0% [+6.2;+14.3] better |
| default_corr vs default_old | +8.4% [+5.7;+21.2] | +8.4% [+5.6;+11.4] (P2|rho0.0992) | W0/B15/15 | +9.3% [+7.5;+19.9] W0/B3/3 | +7.5% [+4.7;+10.4] better |

draft/round e T/round (P4 ρ=0,0992): default_old 3.00 / 3.98, default_corr 2.20 / 2.57, spec_cost 2.11 / 2.65, k3 3.00 / 3.96

#### edit
| confronto | banda: mediana [min;max] | IC95 cella mediana | W/B/n banda | ρ=0,26: mediana [min;max] W/B/n | griglia P4 Δ [IC95] |
|---|---|---|---|---|---|
| spec_cost vs default_corr | +0.4% [-7.1;+1.8] | +0.4% [-0.7;+1.4] (P1|rho0.0590) | W1/B6/15 | +1.4% [-5.4;+1.5] W1/B2/3 | -5.4% [-8.2;-2.6] worse |
| spec_cost vs default_old | +2.8% [-5.4;+4.3] | +2.8% [+0.5;+5.4] (P1|rho0.0791) | W1/B14/15 | +3.9% [-4.1;+4.2] W1/B2/3 | -4.2% [-7.4;-0.9] worse |
| spec_cost vs k3 | +11.5% [+4.1;+15.0] | +11.5% [+8.9;+13.7] (P2|rho0.0590) | W0/B15/15 | +10.9% [+9.6;+15.8] W0/B3/3 | +9.6% [+7.2;+12.1] better |
| default_corr vs default_old | +2.3% [+1.9;+2.5] | +2.3% [+1.0;+3.9] (P2|rho0.1394) | W0/B15/15 | +2.5% [+1.3;+2.6] W0/B3/3 | +1.3% [+0.5;+2.3] better |

draft/round e T/round (P4 ρ=0,0992): default_old 3.00 / 4.96, default_corr 2.85 / 4.77, spec_cost 2.72 / 4.61, k3 3.00 / 3.96

Nota edit: l'unica cella W in banda per SPEC_COST vs default corretto è P4 ρ=0,059 (−7,1% [−9,4;−4,8]); anche la griglia P4 è W (−5,4% [−8,2;−2,6]).
Coerenza: i tok/s stimati coincidono esattamente con quelli di results/v2/holdout_v11_costvariants (stesse politiche, stesse celle).
