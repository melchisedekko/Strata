# Addendum: regola finale H-LW (fissata dal Lead alle 08:09 CET, prima di qualsiasi dato AMD)

Proxy CPU, AL, parametrico. Le soglie qui sotto vengono dal modello s(T)=1+ρ(T−1) con draft a costo zero e non sono misurate. Questo addendum non modifica nessun file hashato.

## Riferimenti (sha256 verificati alle 08:10 CET)

- results/v2/breakeven_dsecond/REPORT.md: `a505947f8446d60ab62e70b0848171363ed70d7651841c22519b943adff95dc7`
- results/v2/breakeven_dsecond/breakeven_dsecond.json: `5eebb31b95417408df73e6c4181f25ae70c2afba48b4e5298a15d8de5d524d62`
- replay/run_breakeven_dsecond.json: `519d09fba57d682edd418082565d52824b010534113828531a4c2c3f250cfc33`

I valori sono letti a piena precisione da breakeven_dsecond.json, sul tune (decisionale) per (d″) = MTP 3 + lookup ≤11 con T=12 righe. La lettura è stata fatta con nice -n 19, finestra 2026-10-25 08:10:15–08:10:15 CET, rc=0.

## 1. Se E-AMD-0 premia (a′) `--spec 8 --mtp-max-t 4`

**GO** se s(12)/s(8), misurato sul binario patchato nella stessa sessione, è **≤ soglia code oppure ≤ soglia edit**. La soglia vale 0,94 × il pareggio tune con gate di (d″) vs (a′).

| dominio | serie | pareggio s12/s8 (piena precisione) | IC95 | soglia = 0,94× (4 dec.) | soglia (piena precisione) |
|---|---|---|---|---|---|
| code | gate (decisionale) | 1.451612903225806 | [1.4146132296609684, 1.4888888888888885] | **1.3645** | 1.3645161290322576 |
| edit | gate (decisionale) | 1.4155844155844153 | [1.3594057976005136, 1.4676723191946974] | **1.3306** | 1.3306493506493502 |
| code | oracolo (secondaria) | 1.4457831325301205 | [1.3940298507462685, 1.4875076490424046] | 1.3590 | 1.3590361445783132 |
| edit | oracolo (secondaria) | 1.441988950276243 | [1.3912918877787985, 1.4889007756084511] | 1.3555 | 1.3554696132596684 |

## 2. Se vince il default (a) `--spec 4`

Nel motore il default diventa T=6 righe con il lookup attivo (generate.cpp L3208-3211; il default è in setup.py L9420). La soglia vale 0,94 × il pareggio tune con gate di (d″) vs (a), sul rapporto s(12)/s(6).

| dominio | serie | pareggio s12/s6 (piena precisione) | IC95 | soglia = 0,94× (4 dec.) | soglia (piena precisione) |
|---|---|---|---|---|---|
| code | gate (decisionale) | 1.8950276243093924 | [1.8235036356416119, 1.9590205782755923] | **1.7813** | 1.7813259668508288 |
| edit | gate (decisionale) | 1.8206039076376554 | [1.6987042010249729, 1.9212667504558243] | **1.7114** | 1.711367673179396 |
| code | oracolo (secondaria) | 1.9212598425196847 | [1.8588279773156897, 1.9711036009789067] | 1.8060 | 1.8059842519685037 |
| edit | oracolo (secondaria) | 1.8620037807183367 | [1.7452590313886693, 1.9535149101087301] | 1.7503 | 1.7502835538752364 |

La regola di GO è la stessa del punto 1: s(12)/s(6), misurato sul binario patchato nella stessa sessione, deve essere ≤ soglia code oppure ≤ soglia edit.

Massimi per costruzione: s12/s8 vale 11/7 = 1.5714; s12/s6 vale 11/5 = 2.2.

## 3. Portata del GO

Il GO autorizza solo la patch completa, con kShape riempita dal profilo s(T) misurato su AMD. Il verdetto vero resta l'A/B live dei tok/s su AMD, con il criterio E-AMD-0: IC95 sopra 0 e nessuna cella W.

## 4. Regressione per T≤8

Se il binario patchato rallenta s(8), il pareggio si ricalcola su quel s(8). Se peggiora anche il default, la perdita è un costo della patch e va nel verdetto.

## 5. Misura

- STRATA_SPEC_T_CYCLE deve includere 6, 8 e 12 nella stessa sessione, sul binario patchato.
- I metadati riportano il numero di expert mancanti per round.
- Guardia CPU per n_tok>8: approvata.

## 6. Chat

Contro (a′) con gate non c'è pareggio, né sul tune né sull'holdout: risulta 'mai', con ΔR=0 e ΔX>0. Il GO vale quindi per code ed edit. Come nota descrittiva, contro (a) chat ha un pareggio minimo con gate (tune ρ\*=0.019, s12/s6=1.1026), che non rientra nella regola.
