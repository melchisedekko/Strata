# Verdetto a due fasce — PROXY teacher-forced tf_d7.jsonl (30 richieste reali, Qwen3.5-2B denso su CPU): candidati MTP reali, lookup ricalcolato con SuffixDrafter (max_match 64); tok/s STIMATI con i profili di costo

Fascia **Strata-plausibile** rho_mtp ∈ {0.059, 0.079, 0.099, 0.119, 0.139}: *fascia plausibile, stima di Scout, da misurare su Strata* (non è una misura); decide la patch. Fascia **proxy** rho_mtp = 0.260 (P4 grezzo, provvisorio): solo robustezza. Forme s(T): P1, P2 (stime da codice), P4 (misurata su CPU, denso, non AMD, provvisoria). Costo additivo s(T)+d·rho_mtp. Ogni cella: Δ tok/s stimato [IC95 bootstrap a cluster].

## Fascia Strata-plausibile [0.06, 0.15]

| confronto | esito (profili OK / tot) | profili con un dominio IC95<0 | code: min…max Δ (IC95 della cella peggiore) | chat: min…max Δ (IC95 della cella peggiore) | edit: min…max Δ (IC95 della cella peggiore) |
|---|---|---|---|---|---|
| H1: gate_v2 vs DraftPolicy default | GO (15/15) | 0 | +4.7…+22.7% (peggiore +4.7% [+1.5, +8.0]) | +8.9…+31.1% (peggiore +8.9% [+3.8, +13.6]) | +5.8…+20.5% (peggiore +5.8% [+1.1, +9.8]) |
| H4(a): gate_v2 vs STRATA_SPEC_COST=1 | NO-GO (9/15) | 0 | +3.1…+22.1% (peggiore +3.1% [+0.1, +5.5]) | -0.8…+0.6% (peggiore -0.8% [-2.3, +0.5]) | +1.8…+19.5% (peggiore +1.8% [-0.9, +4.4]) |
| H4(b): gate_v2 vs k=3 | GO (15/15) | 0 | +8.5…+37.5% (peggiore +8.5% [+4.5, +12.6]) | +9.1…+31.0% (peggiore +9.1% [+4.3, +13.4]) | +9.0…+35.8% (peggiore +9.0% [+4.2, +12.9]) |
| Lead: gate_v2 vs euristica Specu | NO-GO (5/15) | 0 | +1.3…+6.6% (peggiore +1.3% [-3.6, +7.5]) | +7.4…+27.8% (peggiore +7.4% [+3.6, +10.9]) | -1.2…+6.5% (peggiore -1.2% [-13.5, +7.7]) |
| (info) gate_v2 vs Specu+profondità SPEC_COST | NO-GO (7/15) | 0 | +1.6…+5.3% (peggiore +1.6% [-3.0, +7.3]) | +3.3…+7.1% (peggiore +3.3% [+0.9, +6.4]) | -3.5…+4.3% (peggiore -3.5% [-14.3, +4.3]) |
| Specu vs default | NO-GO (9/15) | 0 | -1.2…+21.2% (peggiore -1.2% [-5.6, +3.1]) | +1.0…+3.9% (peggiore +1.0% [-5.2, +6.3]) | -0.7…+17.3% (peggiore -0.7% [-5.1, +4.6]) |
| Specu vs STRATA_SPEC_COST=1 | NO-GO (0/15) | 15 | -2.7…+20.5% (peggiore -2.7% [-7.3, +1.6]) | -21.9…-6.3% (peggiore -21.9% [-24.5, -18.5]) | -4.3…+16.4% (peggiore -4.3% [-11.2, +4.2]) |
| Specu vs k=3 | NO-GO (12/15) | 0 | +2.1…+35.8% (peggiore +2.1% [-3.5, +7.8]) | +1.2…+3.8% (peggiore +1.2% [-5.1, +6.4]) | +2.3…+32.3% (peggiore +2.3% [-2.6, +8.3]) |
| (info) Specu+prof. SPEC_COST vs STRATA_SPEC_COST=1 | NO-GO (0/15) | 15 | -1.5…+20.2% (peggiore -1.5% [-5.8, +2.5]) | -6.9…-2.6% (peggiore -6.9% [-11.5, -3.1]) | -1.8…+18.1% (peggiore -1.8% [-7.6, +4.8]) |

## Fascia proxy 0.26 (robustezza)

| confronto | esito (profili OK / tot) | profili con un dominio IC95<0 | code: min…max Δ (IC95 della cella peggiore) | chat: min…max Δ (IC95 della cella peggiore) | edit: min…max Δ (IC95 della cella peggiore) |
|---|---|---|---|---|---|
| H1: gate_v2 vs DraftPolicy default | GO (3/3) | 0 | +14.5…+29.2% (peggiore +14.5% [+9.8, +18.8]) | +14.0…+31.6% (peggiore +14.0% [+6.4, +21.0]) | +9.7…+18.5% (peggiore +9.7% [+3.7, +16.1]) |
| H4(a): gate_v2 vs STRATA_SPEC_COST=1 | GO (3/3) | 0 | +18.8…+27.8% (peggiore +18.8% [+12.9, +24.0]) | -0.3…+1.1% (peggiore -0.3% [-1.2, +0.7]) | +5.0…+16.3% (peggiore +5.0% [+1.3, +9.7]) |
| H4(b): gate_v2 vs k=3 | GO (3/3) | 0 | +22.1…+47.0% (peggiore +22.1% [+14.8, +28.3]) | +14.1…+31.2% (peggiore +14.1% [+6.8, +21.0]) | +16.4…+35.9% (peggiore +16.4% [+11.8, +21.5]) |
| Lead: gate_v2 vs euristica Specu | NO-GO (1/3) | 0 | -2.8…+4.8% (peggiore -2.8% [-8.1, +4.2]) | +7.8…+24.4% (peggiore +7.8% [+4.6, +10.6]) | -6.8…+0.7% (peggiore -6.8% [-20.2, +4.8]) |
| (info) gate_v2 vs Specu+profondità SPEC_COST | NO-GO (0/3) | 0 | -2.6…+3.7% (peggiore -2.6% [-7.4, +3.5]) | +2.8…+5.3% (peggiore +2.8% [+0.7, +5.3]) | -8.6…-2.4% (peggiore -8.6% [-21.3, +2.2]) |
| Specu vs default | GO (3/3) | 0 | +9.2…+32.9% (peggiore +9.2% [+4.7, +14.3]) | +5.8…+5.8% (peggiore +5.8% [-0.6, +11.5]) | +8.9…+27.1% (peggiore +8.9% [+3.1, +16.7]) |
| Specu vs STRATA_SPEC_COST=1 | NO-GO (0/3) | 3 | +13.3…+31.5% (peggiore +13.3% [+6.9, +20.6]) | -19.8…-6.2% (peggiore -19.8% [-22.2, -16.7]) | +4.3…+24.8% (peggiore +4.3% [-5.5, +16.4]) |
| Specu vs k=3 | GO (3/3) | 0 | +16.5…+51.1% (peggiore +16.5% [+9.5, +24.1]) | +5.5…+5.9% (peggiore +5.5% [-3.8, +13.5]) | +15.6…+45.8% (peggiore +15.6% [+7.8, +25.7]) |
| (info) Specu+prof. SPEC_COST vs STRATA_SPEC_COST=1 | NO-GO (1/3) | 2 | +14.5…+31.3% (peggiore +14.5% [+8.4, +21.2]) | -5.3…-2.0% (peggiore -5.3% [-8.4, -2.4]) | +7.6…+27.3% (peggiore +7.6% [-0.7, +17.3]) |

## Dettaglio a rho_mtp = 0.099 (centro della fascia plausibile) e 0.26

| forma | rho | dominio | gate_v2 vs default | vs SPEC_COST=1 | vs k3 | vs Specu | Specu vs SPEC_COST=1 | k fisso migliore |
|---|---|---|---|---|---|---|---|---|
| P1 | 0.099 | code | +6.5% [+3.7, +9.4] | +8.7% [+6.0, +11.4] | +10.6% [+6.6, +14.5] | +5.2% [+0.8, +11.3] | +3.3% [-2.2, +9.0] | 4 |
| P1 | 0.099 | chat | +30.7% [+18.9, +41.8] | -0.8% [-2.3, +0.5] | +30.4% [+18.5, +41.6] | +26.3% [+22.0, +29.9] | -21.5% [-24.1, -17.9] | 1 |
| P1 | 0.099 | edit | +7.5% [+3.4, +11.4] | +1.8% [-0.9, +4.4] | +11.0% [+6.4, +14.7] | +5.6% [-3.2, +13.8] | -3.6% [-10.4, +4.6] | 2 |
| P1 | 0.260 | code | +14.5% [+9.8, +18.8] | +18.8% [+12.9, +24.0] | +22.1% [+14.8, +28.3] | +4.8% [+0.4, +11.4] | +13.3% [+6.9, +20.6] | 2 |
| P1 | 0.260 | chat | +31.6% [+19.8, +43.0] | -0.3% [-1.2, +0.7] | +31.2% [+19.2, +42.3] | +24.4% [+20.2, +27.5] | -19.8% [-22.2, -16.7] | 1 |
| P1 | 0.260 | edit | +9.7% [+3.7, +16.1] | +5.0% [+1.3, +9.7] | +16.4% [+11.8, +21.5] | +0.7% [-9.4, +10.4] | +4.3% [-5.5, +16.4] | 1 |
| P2 | 0.099 | code | +13.4% [+8.0, +18.3] | +12.5% [+7.3, +17.1] | +24.7% [+16.1, +32.6] | +3.7% [-0.6, +9.5] | +8.4% [+3.6, +13.7] | 4 |
| P2 | 0.099 | chat | +12.9% [+5.5, +19.6] | -0.1% [-1.9, +1.6] | +13.0% [+6.1, +19.4] | +10.2% [+6.4, +14.1] | -9.4% [-13.2, -6.0] | 1 |
| P2 | 0.099 | edit | +12.5% [+10.2, +15.0] | +10.6% [+6.3, +15.3] | +24.5% [+18.7, +31.0] | +4.9% [-0.4, +9.3] | +5.4% [-1.6, +14.3] | 4 |
| P2 | 0.260 | code | +21.4% [+14.0, +29.2] | +20.0% [+13.4, +27.2] | +36.5% [+25.1, +48.4] | -1.6% [-5.6, +2.9] | +22.0% [+16.2, +29.0] | 4 |
| P2 | 0.260 | chat | +16.4% [+7.9, +24.2] | +0.4% [-2.1, +3.6] | +16.5% [+8.3, +24.2] | +10.0% [+6.3, +13.3] | -8.7% [-12.2, -5.4] | 1 |
| P2 | 0.260 | edit | +14.1% [+4.9, +22.0] | +11.1% [+2.6, +20.1] | +29.1% [+18.7, +40.9] | -4.5% [-16.5, +5.5] | +16.4% [+6.2, +30.1] | 3 |
| P4 | 0.099 | code | +19.9% [+12.8, +26.8] | +19.5% [+12.9, +25.7] | +33.6% [+22.7, +44.1] | +2.5% [-1.9, +8.6] | +16.6% [+11.2, +22.8] | 7 |
| P4 | 0.099 | chat | +10.3% [+4.1, +15.9] | -0.1% [-1.1, +1.2] | +10.4% [+4.6, +15.7] | +7.9% [+4.0, +11.8] | -7.4% [-10.8, -4.1] | 2 |
| P4 | 0.099 | edit | +16.0% [+11.4, +21.6] | +15.5% [+9.3, +23.1] | +30.0% [+20.6, +41.3] | +2.1% [-2.7, +5.7] | +13.2% [+5.3, +23.4] | 4 |
| P4 | 0.260 | code | +29.2% [+18.1, +41.4] | +27.8% [+17.2, +39.6] | +47.0% [+30.7, +64.6] | -2.8% [-8.1, +4.2] | +31.5% [+24.2, +40.3] | 4 |
| P4 | 0.260 | chat | +14.0% [+6.4, +21.0] | +1.1% [-1.3, +4.1] | +14.1% [+6.8, +21.0] | +7.8% [+4.6, +10.6] | -6.2% [-9.2, -3.4] | 1 |
| P4 | 0.260 | edit | +18.5% [+6.1, +32.2] | +16.3% [+3.5, +32.0] | +35.9% [+20.1, +56.5] | -6.8% [-20.2, +4.8] | +24.8% [+12.0, +42.5] | 3 |
