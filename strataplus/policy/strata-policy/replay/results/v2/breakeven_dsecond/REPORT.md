# Pareggio (d″) = MTP 3 draft + lookup ≤11 token, T=12 righe — proxy CPU, AL, parametrico

**Proxy CPU, AL, parametrico.** Gli AL vengono da un replay teacher-forced su tracce. ρ\* e i rapporti di pareggio usano il modello s(T)=1+ρ(T−1) con draft a costo zero: sono parametrici e non misurati. Nessun tok/s.

## Riferimenti

- Run file prefissato: replay/run_breakeven_dsecond.json (`519d09fba57d682edd418082565d52824b010534113828531a4c2c3f250cfc33`), scritto alle 08:06:54 CET prima di aprire le tracce.
- Script: replay/breakeven_dsecond.py (`1f2a10e2f4360a8b74d42dc8c09b3d2d654d9cf34c4117ff2cf5380425d95a19`).
- Funzioni verbatim da lookup_rule_al_addendum.py (b402c026…), con assert di identità testuale. Ciclo e bootstrap sono quelli di breakeven_dprime.py (71e8823d…): B=2000, seed 0, cluster per sessione, repliche identiche.
- Tracce: tune 87efe507…; holdout code a9e247b2…, chat b5380c42…, edit d9a48386… (le stesse di run_breakeven_dprime.json).
- Lib: libstrata_spec_capi.so 8fb27b0d…

## Convenzione (Lead, 08:06)

- T è il numero di righe della verify: window[0]=x più T−1 draft (generate.cpp L14922-14928). Il lookup propone al più S−1 token (sfx.propose(S−1), generate.cpp L14897). Quindi la patch T=12 dà lookup ≤11 token.
- Citazione corretta: il passaggio spec 4→6 con lookup è in **generate.cpp L3208-3211** (mtp_max_t=spec, spec=min(spec+2,8)). **setup.py L9420** contiene solo il default `--spec 4 --spec-min-p 0.5`.

| braccio | MTP draft | lookup max token | T (righe max) | righe MTP / lookup max |
|---|---|---|---|---|
| (a) installata: --spec 4 → spec 6 | 3 | 5 | 6 | 4 / 6 |
| (a′) --spec 8 --mtp-max-t 4 | 3 | 7 | 8 | 4 / 8 |
| (d″) patch T=12 | 3 | 11 | 12 | 4 / 12 |
| (d′) solo controllo | 3 | 12 | — | 4 / 13 |

Le righe massime effettive coincidono con l'etichetta T per (a), (a′) e (d″).

- Rapporti usati: s(12)/s(8)=(1+11ρ\*)/(1+7ρ\*) contro (a′); s(12)/s(6)=(1+11ρ\*)/(1+5ρ\*) contro (a). s(12)/s(4) non è usato.
- Massimi per costruzione: s12/s8 vale 11/7=1.5714 per ρ→∞ e 23/15=1.5333 a ρ=2; s12/s6 vale 2.2 per ρ→∞ e 23/11=2.0909 a ρ=2.
- Lettura: (d″) batte il braccio base se il rapporto di costo misurato fra una verify a 12 righe e una a 8 (o 6) righe è **sotto** il rapporto di pareggio.

## Controlli (tutti superati, via assert)

- AL di (a) e (a′), oracolo e gate, con IC95: identici bit per bit a breakeven_dprime.json (1da55ce5…), in 6 insiemi su 6.
- Con dmax 12 lo script riproduce (d′) di breakeven_dprime.json in modo esatto: AL e IC95, ρ\* (punto, forma chiusa, IC95), rapporti s12/s8 e s12/s6 (punto e IC95), per entrambe le serie.
- Il lookup a 16 confrontato col cap 7 della traccia dà 0 mismatch su tutti gli insiemi.
- Forma chiusa (R_base−R_x)/(X_x−X_base) uguale al ρ\* da griglia e bisezione in ogni cella.

## AL [IC95 bootstrap su sessioni]

| insieme | n req | serie | (a) T=6 | (a′) T=8 | (d″) T=12 |
|---|---|---|---|---|---|
| tune code | 10 | oracolo | 5.0247 [4.7882, 5.2893] | 6.0446 [5.5865, 6.5645] | 7.4000 [6.5281, 8.4830] |
| tune code | 10 | gate | 4.8840 [4.5929, 5.1957] | 5.7867 [5.2818, 6.3594] | 7.2249 [6.3152, 8.3630] |
| tune edit | 10 | oracolo | 4.6886 [4.0125, 5.4936] | 5.4008 [4.3537, 6.8817] | 6.4975 [4.8485, 9.1429] |
| tune edit | 10 | gate | 4.4138 [3.6261, 5.4468] | 5.0593 [3.9382, 6.8085] | 6.0094 [4.3682, 9.0141] |
| tune chat | 10 | oracolo | 2.5846 [2.3146, 2.9547] | 2.5900 [2.3188, 2.9590] | 2.5954 [2.3230, 2.9666] |
| tune chat | 10 | gate | 2.0032 [1.6798, 2.4711] | 2.0097 [1.6821, 2.4810] | 2.0097 [1.6821, 2.4810] |
| holdout code | 30 | oracolo | 5.0725 [4.8454, 5.2864] | 6.2125 [5.8007, 6.6352] | 7.8031 [7.0320, 8.6390] |
| holdout code | 30 | gate | 4.8849 [4.6016, 5.1637] | 5.9138 [5.4466, 6.4247] | 7.4137 [6.5772, 8.3565] |
| holdout edit | 30 | oracolo | 4.8475 [4.4842, 5.2361] | 5.7195 [5.1081, 6.4132] | 7.0526 [5.9935, 8.3773] |
| holdout edit | 30 | gate | 4.6321 [4.2317, 5.0663] | 5.4298 [4.7787, 6.1605] | 6.6762 [5.5929, 8.0384] |
| holdout chat | 30 | oracolo | 2.7821 [2.5895, 3.0202] | 2.7885 [2.5961, 3.0275] | 2.7906 [2.5974, 3.0300] |
| holdout chat | 30 | gate | 2.2815 [2.0690, 2.5515] | 2.2858 [2.0705, 2.5565] | 2.2858 [2.0705, 2.5565] |

Cattura gate/oracolo di (d″), e quota di round sul ramo lookup col gate (con i token medi nel ramo):

| insieme | cattura [IC95] | round lookup | token medi lookup |
|---|---|---|---|
| tune code | 0.9763 [0.9438, 1.0067] | 0.5385 | 10.7253 |
| tune edit | 0.9249 [0.8880, 0.9861] | 0.4554 | 10.0928 |
| tune chat | 0.7744 [0.7209, 0.8453] | 0.0325 | 4.0000 |
| holdout code | 0.9501 [0.9249, 0.9749] | 0.5655 | 10.7537 |
| holdout edit | 0.9466 [0.9294, 0.9669] | 0.5160 | 10.2517 |
| holdout chat | 0.8191 [0.7932, 0.8482] | 0.0559 | 3.5730 |

## Pareggi ρ\* e rapporto di pareggio [IC95]

Il tune è decisionale. L'holdout è solo descrittivo: è già stato usato e nessun parametro è scelto su di esso.

| insieme | serie | ρ\* vs (a′) | s12/s8 | ρ\* vs (a) | s12/s6 | ΔR, ΔX vs (a′) |
|---|---|---|---|---|---|---|
| tune code | gate | 0.5385 [0.3777, 0.8462] | 1.4516 [1.4146, 1.4889] | 0.5870 [0.4375, 0.7959] | 1.8950 [1.8235, 1.9590] | 42, 78 |
| tune code | oracolo | 0.5068 [0.3173, 0.8299] | 1.4458 [1.3940, 1.4875] | 0.6610 [0.5035, 0.8485] | 1.9213 [1.8588, 1.9711] | 37, 73 |
| tune edit | gate | 0.3810 [0.2422, 0.6439] | 1.4156 [1.3594, 1.4677] | 0.4326 [0.2788, 0.6610] | 1.8206 [1.6987, 1.9213] | 40, 105 |
| tune edit | oracolo | 0.4878 [0.3103, 0.8463] | 1.4420 [1.3913, 1.4889] | 0.5101 [0.3278, 0.7737] | 1.8620 [1.7453, 1.9535] | 40, 82 |
| tune chat | gate | mai [0.0000, 0.0000] (boot mai 1.000) | mai [1.0000, 1.0000] | 0.0187 [0.0000, 0.0450] (boot mai 0.104) | 1.1026 [1.0000, 1.2206] | 0, 75 |
| tune chat | oracolo | 0.0256 [0.0000, 0.0588] (boot mai 0.350) | 1.0870 [1.0000, 1.1667] | 0.0392 [0.0000, 0.0820] (boot mai 0.104) | 1.1967 [1.0000, 1.3489] | 1, 39 |
| holdout code | gate | 0.6100 [0.4190, 0.9286] | 1.4630 [1.4261, 1.4952] | 0.7034 [0.5735, 0.8780] | 1.9343 [1.8897, 1.9774] | 122, 200 |
| holdout code | oracolo | 0.6223 [0.4632, 0.8392] | 1.4647 [1.4367, 1.4883] | 0.7640 [0.6580, 0.8780] | 1.9510 [1.9203, 1.9774] | 117, 188 |
| holdout edit | gate | 0.5972 [0.3856, 0.9926] | 1.4611 [1.4169, 1.4995] | 0.5611 [0.3979, 0.7765] | 1.8847 [1.7986, 1.9542] | 129, 216 |
| holdout edit | oracolo | 0.5232 [0.3631, 0.7641] | 1.4489 [1.4101, 1.4814] | 0.5874 [0.4372, 0.7580] | 1.8952 [1.8234, 1.9495] | 124, 237 |
| holdout chat | gate | mai [0.0000, 0.0000] (boot mai 1.000) | mai [1.0000, 1.0000] | 0.0093 [0.0000, 0.0255] (boot mai 0.042) | 1.0536 [1.0000, 1.1359] | 0, 219 |
| holdout chat | oracolo | 0.0085 [0.0000, 0.0263] (boot mai 0.345) | 1.0320 [1.0000, 1.0889] | 0.0234 [0.0048, 0.0503] (boot mai 0.016) | 1.1257 [1.0280, 1.2412] | 1, 118 |

## Soglie di go (regola del Lead, fissata nel run file prima dei numeri)

soglia_go = 0.94 × rapporto di pareggio s(12)/s(8), su tune, (d″) contro (a′). La serie gate è decisionale; l'oracolo è una lettura secondaria.

| dominio | serie | pareggio s12/s8 [IC95] | soglia_go = 0.94× |
|---|---|---|---|
| code | gate (decisionale) | 1.4516 [1.4146, 1.4889] | **1.3645** |
| code | oracolo (secondaria) | 1.4458 [1.3940, 1.4875] | **1.3590** |
| edit | gate (decisionale) | 1.4156 [1.3594, 1.4677] | **1.3306** |
| edit | oracolo (secondaria) | 1.4420 [1.3913, 1.4889] | **1.3555** |

Chat non rientra nella regola. Col gate, il pareggio di (d″) contro (a′) è 'mai' sia su tune sia su holdout: ΔR=0 e ΔX>0, quindi nessun pareggio esiste.

## Riga descrittiva (d″) − (d′)

| insieme | serie | ΔAL | ΔAL rel [IC95] | ΔR | ΔX | ρ\* vs (a′) d″ / d′ | ρ\* vs (a) d″ / d′ |
|---|---|---|---|---|---|---|---|
| tune code | gate | -0.1306 | -0.0178 [-0.0419, +0.0060] | +3 | -22 | 0.5385 / 0.4500 | 0.5870 / 0.5250 |
| tune code | oracolo | -0.2312 | -0.0303 [-0.0536, -0.0065] | +5 | +6 | 0.5068 / 0.6269 | 0.6610 / 0.7411 |
| tune edit | gate | -0.1445 | -0.0235 [-0.0519, -0.0073] | +5 | -6 | 0.3810 / 0.4054 | 0.4326 / 0.4457 |
| tune edit | oracolo | -0.2394 | -0.0355 [-0.0709, -0.0153] | +7 | -3 | 0.4878 / 0.5529 | 0.5101 / 0.5461 |
| tune chat | gate | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0 | -15 | mai / mai | 0.0187 / 0.0164 |
| tune chat | oracolo | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0 | -9 | 0.0256 / 0.0208 | 0.0392 / 0.0333 |
| holdout code | gate | -0.2716 | -0.0353 [-0.0537, -0.0184] | +17 | -34 | 0.6100 / 0.5940 | 0.7034 / 0.6856 |
| holdout code | oracolo | -0.2648 | -0.0328 [-0.0478, -0.0185] | +15 | -4 | 0.6223 / 0.6875 | 0.7640 / 0.8006 |
| holdout edit | gate | -0.1333 | -0.0196 [-0.0373, -0.0050] | +11 | -152 | 0.5972 / 0.3804 | 0.5611 / 0.4360 |
| holdout edit | oracolo | -0.1767 | -0.0244 [-0.0438, -0.0090] | +13 | -55 | 0.5232 / 0.4692 | 0.5874 / 0.5460 |
| holdout chat | gate | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0 | -51 | mai / mai | 0.0093 / 0.0081 |
| holdout chat | oracolo | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0 | -26 | 0.0085 / 0.0069 | 0.0234 / 0.0203 |

Nota: d′ era etichettato T=12 ma usava fino a 13 righe, mentre d″ ne usa al massimo 12. I rapporti di d′ in breakeven_dprime.json sono quindi calcolati con un'etichetta T che sottostima le righe effettive.

## Anomalie e limiti

1. **Citazione.** Nei miei report hashati non risulta un'attribuzione a setup.py della logica 4→6. breakeven_dprime e ceiling_installed_cfg citano generate.cpp L3208-3211; lookup_rule_al e il suo addendum citano setup.py L9420 solo per il default --spec 4. Qui ho applicato la correzione come richiesta.
2. **Gate con ρ\* sopra l'oracolo.** Con il gate, ρ\* può superare quello dell'oracolo. Esempi: holdout edit vs (a′) 0.597 contro 0.523; tune code 0.538 contro 0.507. Il motivo è che l'oracolo prende il ramo che massimizza a (a parità vince il lookup a 12 righe) e quindi spende più righe. Non è un errore, ma l'oracolo non è un limite superiore per ρ\*.
3. **Path-dependence.** Togliere il dodicesimo token di lookup cambia la sequenza delle posizioni. Per questo ΔX fra d″ e d′ non è sempre negativo (per esempio tune code oracolo ΔX=+6).
4. **Campione piccolo.** Il tune ha 10 sessioni per dominio e IC95 larghi (edit tune AL (d″) gate [4.37, 9.01]). La soglia di go è un valore puntuale: l'IC del pareggio, per esempio code gate [1.415, 1.489], dà la sua incertezza.
5. **Modello di costo.** Il modello è parametrico e lineare, con draft a costo zero. Non tiene conto del costo reale della verify a 12 righe (kVerifyMaxT oggi vale 8, quindi serve la patch), né del costo del lookup.

Finestra CPU (CET): 2026-10-25 08:07:50 – 08:07:57, rc=0. Eseguito con nice -n 19 e OMP/OPENBLAS/MKL_NUM_THREADS=1.
