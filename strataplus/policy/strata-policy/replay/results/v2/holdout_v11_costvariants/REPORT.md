# Holdout v1.1 — varianti di costo del draft per A (tmax=5) — RIVALUTAZIONE POST-HOC, SOLO DESCRITTIVA
Holdout già usato; non è una nuova validazione; nessuna regola di decisione applicata; A/B non riaperto; nessuna ritaratura;
parametri congelati (frozen_params_v3.json invariato). tok/s STIMATI dal modello di costo (non misure). IC95 = sim2.boot_ratio B=2000 seed 0, cluster = sessione.
Script: replay/holdout_v11_costvariants.py (sim2/postprocess non modificati; walk2 = sim2.walk L81-103 con d pagato separato dal d del gate).
Varianti: ORIG = costo replay (d del gate); M-full = 4 draft/round; M-real = max(d,1); M-cap = tetto fissato a fine round r
(regola 'prev': cap iniziale tmax-1=4, poi cap=max(1,w), w = profondità dove si fermerebbe il test di valore congelato usando i draft visti
fino al tetto e oltre l'estrapolazione _mtp_haz del gate; skip → 1 passo; d usabile = min(d_gate, cap)). Regola 'cap=tmax-1' ≡ M-full.
default_old = 3 draft/finestra 4 (= motore con --spec-min-p 0); default_corr = --spec-min-p 0.5 (setup.py L9420) con taglio su mtp_p delle tracce TF.
Limite: le mtp_p vengono dal proxy llama.cpp (qwen35-2b-mtp, dmax 7), non dal draft layer di Strata: la calibrazione di p≥0.5 può differire.

### Banda ρ 0,06–0,15 (P1/P2/P4 × 5 ρ = 15 celle/dominio), V1 (V2 identico)
mediana Δ tok/s STIMATO [min;max fra celle] W=chiaramente peggio (IC95 hi<0) / B=chiaramente meglio (lo>0) / celle

| dominio | variante | default_old | default_corr | spec_cost | k3 |
|---|---|---|---|---|---|
| code | A_ORIG | +6.9% [+3.4;+10.8] W0/B15/15 | +6.2% [+3.4;+10.6] W0/B15/15 | +5.5% [+2.2;+9.7] W0/B15/15 | +14.3% [+7.2;+23.2] W0/B15/15 |
| code | A_Mfull | -4.7% [-7.2;-1.6] W15/B0/15 | -5.2% [-7.4;+1.0] W13/B1/15 | -5.8% [-8.8;-2.8] W15/B0/15 | +2.5% [+0.0;+5.1] W0/B13/15 |
| code | A_Mreal | +4.0% [+1.4;+5.9] W0/B15/15 | +3.8% [+1.4;+6.1] W0/B15/15 | +2.5% [+1.3;+5.1] W0/B15/15 | +11.7% [+6.4;+17.8] W0/B15/15 |
| code | A_Mcap | +2.9% [+0.8;+4.8] W0/B14/15 | +2.7% [+0.8;+5.1] W0/B13/15 | +1.7% [+0.3;+4.0] W0/B12/15 | +10.7% [+5.2;+16.4] W0/B15/15 |
| chat | A_ORIG | +12.2% [+9.0;+24.3] W0/B15/15 | +3.2% [+2.1;+4.9] W0/B15/15 | +1.5% [-1.4;+2.5] W1/B10/15 | +12.6% [+9.5;+24.6] W0/B15/15 |
| chat | A_Mfull | +2.9% [-1.2;+17.4] W0/B8/15 | -6.0% [-8.8;-2.7] W15/B0/15 | -7.8% [-12.1;-4.4] W15/B0/15 | +3.3% [-0.8;+17.6] W0/B10/15 |
| chat | A_Mreal | +11.9% [+9.3;+23.8] W0/B15/15 | +3.2% [+2.0;+4.4] W0/B14/15 | +1.4% [-1.4;+2.2] W3/B9/15 | +12.3% [+9.7;+24.1] W0/B15/15 |
| chat | A_Mcap | +6.6% [+4.1;+23.3] W0/B15/15 | -1.7% [-1.9;+1.8] W8/B2/15 | -3.2% [-4.2;-1.6] W15/B0/15 | +7.0% [+4.6;+23.6] W0/B15/15 |
| edit | A_ORIG | +7.1% [+3.0;+10.4] W0/B15/15 | +4.8% [+1.1;+8.0] W0/B15/15 | +4.0% [+0.7;+8.9] W0/B14/15 | +14.5% [+8.5;+23.0] W0/B15/15 |
| edit | A_Mfull | -4.7% [-7.5;-1.1] W14/B0/15 | -6.6% [-9.5;-3.5] W15/B0/15 | -6.7% [-10.4;+0.7] W14/B0/15 | +3.1% [+1.3;+4.9] W0/B13/15 |
| edit | A_Mreal | +4.1% [+1.1;+5.9] W0/B14/15 | +1.8% [-0.8;+3.6] W0/B11/15 | +1.3% [-1.1;+6.8] W1/B9/15 | +11.9% [+7.2;+17.3] W0/B15/15 |
| edit | A_Mcap | +3.4% [+0.8;+4.9] W0/B14/15 | +1.3% [-1.1;+2.4] W1/B6/15 | +0.6% [-1.6;+6.5] W1/B1/15 | +11.1% [+6.5;+16.3] W0/B15/15 |

### Controllo ρ=0,26 (P1/P2/P4 = 3 celle/dominio)

| dominio | variante | default_old | default_corr | spec_cost | k3 |
|---|---|---|---|---|---|
| code | A_ORIG | +19.7% [+13.9;+21.5] W0/B3/3 | +19.2% [+12.6;+19.4] W0/B3/3 | +18.7% [+12.1;+20.5] W0/B3/3 | +33.0% [+20.6;+36.9] W0/B3/3 |
| code | A_Mfull | -10.0% [-10.6;-7.2] W3/B0/3 | -10.3% [-12.2;-8.2] W3/B0/3 | -10.7% [-11.4;-8.6] W3/B0/3 | +0.0% [-1.6;+0.7] W1/B0/3 |
| code | A_Mreal | +11.2% [+8.2;+11.4] W0/B3/3 | +9.5% [+7.0;+10.7] W0/B3/3 | +10.2% [+6.5;+10.4] W0/B3/3 | +23.5% [+14.6;+25.5] W0/B3/3 |
| code | A_Mcap | +9.6% [+7.1;+9.6] W0/B3/3 | +7.7% [+5.9;+9.2] W0/B3/3 | +8.7% [+5.4;+8.7] W0/B3/3 | +21.9% [+13.4;+23.5] W0/B3/3 |
| chat | A_ORIG | +16.5% [+14.8;+25.7] W0/B3/3 | +6.6% [+4.9;+6.7] W0/B3/3 | +4.3% [+1.0;+4.7] W0/B3/3 | +17.1% [+15.3;+26.1] W0/B3/3 |
| chat | A_Mfull | -4.4% [-5.0;+2.7] W2/B1/3 | -12.6% [-14.3;-11.7] W3/B0/3 | -14.5% [-17.5;-13.4] W3/B0/3 | -4.0% [-4.6;+3.0] W2/B1/3 |
| chat | A_Mreal | +16.1% [+14.4;+24.7] W0/B3/3 | +6.2% [+4.0;+6.4] W0/B3/3 | +3.8% [+0.2;+4.4] W0/B2/3 | +16.6% [+14.9;+25.1] W0/B3/3 |
| chat | A_Mcap | +6.0% [+4.8;+18.4] W0/B3/3 | -2.6% [-3.0;-1.2] W2/B0/3 | -4.9% [-5.1;-4.4] W3/B0/3 | +6.5% [+5.2;+18.7] W0/B3/3 |
| edit | A_ORIG | +17.7% [+14.1;+19.0] W0/B3/3 | +16.0% [+11.2;+16.1] W0/B3/3 | +14.5% [+9.5;+22.7] W0/B3/3 | +32.5% [+21.4;+34.5] W0/B3/3 |
| edit | A_Mfull | -10.2% [-12.0;-6.5] W3/B0/3 | -12.4% [-13.2;-8.9] W3/B0/3 | -10.2% [-13.6;-8.3] W3/B0/3 | +0.0% [-0.5;+0.5] W0/B0/3 |
| edit | A_Mreal | +9.6% [+8.4;+10.1] W0/B3/3 | +7.4% [+5.7;+8.1] W0/B3/3 | +6.0% [+4.1;+14.3] W0/B3/3 | +22.7% [+15.4;+25.2] W0/B3/3 |
| edit | A_Mcap | +7.3% [+6.7;+8.4] W0/B3/3 | +5.3% [+4.6;+5.7] W0/B3/3 | +4.3% [+3.0;+11.3] W0/B3/3 | +20.8% [+14.2;+21.9] W0/B3/3 |

### Controllo P4 griglia cost_T_d[T, d_pagato] (1 cella/dominio): Δ [IC95]

| dominio | variante | default_old | default_corr | spec_cost | k3 |
|---|---|---|---|---|---|
| code | A_ORIG | +24.3% [+21.7;+26.9] better | +22.2% [+19.9;+24.4] better | +23.2% [+20.7;+25.8] better | +40.1% [+34.9;+45.4] better |
| code | A_Mfull | -10.6% [-11.8;-9.4] worse | -12.1% [-13.3;-10.8] worse | -11.4% [-12.5;-10.2] worse | +0.8% [-0.8;+2.4] neutral |
| code | A_Mreal | +11.5% [+10.0;+13.0] better | +9.6% [+8.1;+11.0] better | +10.5% [+9.2;+11.9] better | +25.7% [+22.2;+29.2] better |
| code | A_Mcap | +9.8% [+7.6;+11.9] better | +7.9% [+6.0;+9.8] better | +8.8% [+6.7;+11.0] better | +23.7% [+19.3;+28.2] better |
| chat | A_ORIG | +14.9% [+10.9;+19.2] better | +7.0% [+5.0;+9.2] better | +4.9% [+3.3;+6.6] better | +15.4% [+11.0;+20.5] better |
| chat | A_Mfull | -4.9% [-6.4;-3.2] worse | -11.5% [-14.0;-8.5] worse | -13.2% [-16.0;-9.8] worse | -4.4% [-6.0;-2.7] worse |
| chat | A_Mreal | +14.6% [+11.0;+18.5] better | +6.7% [+4.9;+8.7] better | +4.6% [+3.0;+6.4] better | +15.1% [+11.3;+19.2] better |
| chat | A_Mcap | +4.9% [+1.7;+8.1] better | -2.4% [-3.9;-0.7] worse | -4.2% [-5.7;-2.7] worse | +5.4% [+1.7;+9.2] better |
| edit | A_ORIG | +20.2% [+17.0;+23.5] better | +18.6% [+15.0;+22.4] better | +25.4% [+19.0;+32.3] better | +37.4% [+30.1;+45.0] better |
| edit | A_Mfull | -12.1% [-13.4;-10.7] worse | -13.2% [-14.4;-11.9] worse | -8.3% [-10.7;-5.7] worse | +0.5% [-1.6;+2.6] neutral |
| edit | A_Mreal | +9.8% [+7.9;+11.6] better | +8.3% [+6.3;+10.3] better | +14.5% [+10.1;+19.2] better | +25.5% [+20.7;+30.2] better |
| edit | A_Mcap | +7.1% [+4.9;+9.3] better | +5.7% [+2.8;+8.4] better | +11.7% [+6.5;+17.2] better | +22.4% [+16.7;+28.0] better |

### Draft per round (P4 ρ=0,0992): d del gate / d pagato

- code: default_old 3.00/3.00, default_corr 2.91/2.91, spec_cost 2.84/2.84, k3 3.00/3.00, A_ORIG 0.85/0.85, A_Mfull 1.20/4.00, A_Mreal 0.86/1.56, A_Mcap 0.85/1.68
- chat: default_old 3.00/3.00, default_corr 2.20/2.20, spec_cost 2.11/2.11, k3 3.00/3.00, A_ORIG 2.07/2.07, A_Mfull 2.38/4.00, A_Mreal 2.05/2.09, A_Mcap 1.75/2.41
- edit: default_old 3.00/3.00, default_corr 2.85/2.85, spec_cost 2.72/2.72, k3 3.00/3.00, A_ORIG 0.98/0.98, A_Mfull 1.16/4.00, A_Mreal 1.02/1.63, A_Mcap 0.99/1.81
