# Ricognizione H1 — addendum costo del draft (25/10/2026, CET). Non sostituisce ricognizione_H1.md.
Tutto post-hoc e descrittivo sull'holdout v1.1 già usato; parametri congelati; tok/s STIMATI; mtp_p dal proxy llama.cpp 2B.

1. Il replay ORIG addebitava il draft con la d del gate (skip/lookup = 0 draft), ma il motore disegna la catena a fine round precedente:
   il risparmio non esiste nel motore com'è (P6 non salta né ferma il draft).
2. Varianti di costo per A (tmax=5), banda ρ 0,06–0,15, A vs SPEC_COST, mediana [min;max] W/B su 15 celle
   (results/v2/holdout_v11_costvariants/REPORT.md):
   | variante | code | chat | edit |
   |---|---|---|---|
   | ORIG | +5,5% [+2,2;+9,7] W0/B15 | +1,5% [−1,4;+2,5] W1/B10 | +4,0% [+0,7;+8,9] W0/B14 |
   | M-full (catena intera) | −5,8% [−8,8;−2,8] W15/B0 | −7,8% [−12,1;−4,4] W15/B0 | −6,7% [−10,4;+0,7] W14/B0 |
   | M-real (max(d,1), chain_rule) | +2,5% [+1,3;+5,1] W0/B15 | +1,4% [−1,4;+2,2] W3/B9 | +1,3% [−1,1;+6,8] W1/B9 |
   | M-cap ('prev', tetto fissato prima del draft) | +1,7% [+0,3;+4,0] W0/B12 | −3,2% [−4,2;−1,6] W15/B0 | +0,6% [−1,6;+6,5] W1/B1 |
   La d di GateV2 nasce da un test sequenziale sui draft già calcolati (sim2.py L473-491): M-real è realizzabile solo come chain_rule.
3. min_p reale del default: setup.py L9420 scrive --spec-min-p 0.5 (CLI default 0.0, generate.cpp L705). Con min_p 0,5 il default taglia catena
   (mtp.cpp L1689) e finestra (generate.cpp L14885-14887). SPEC_COST ignora min_p (chain_rule al posto del test, L1689; ramo finestra `else if`, L14883-14885).
4. SPEC_COST vs default installato (min_p 0,5), banda, mediana [min;max] W/B (results/v2/holdout_v11_speccost_vs_default/REPORT.md):
   code +0,6% [+0,1;+3,9] W0/B7; chat +1,7% [+1,5;+3,7] W0/B15; edit +0,4% [−7,1;+1,8] W1/B6.
5. Verdetto: P6 resta locale e NON si accende; P7/P6b NO-GO in questo giro; nessuna patch del gate. Candidata per il giro GPU: chain_rule (M-real),
   da misurare con attesa host e mtp_p vere. Vedi patches/STATUS_P6_NON_ACCENDERE.md.
