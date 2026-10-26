# Addendum C e D alla regola min(match,16): colonna (a′) e rapporti di pareggio. Solo AL; pareggi PARAMETRICI, non misurati

## Riferimenti
- Addendum: replay/run_lookup_rule_addendum.json, sha256 f151f9852e0fd551c44ff3d13a864613006b75b901c1ac201f60268fbe370a64.
  - Scritto alle 07:02:48 CET, in sola lettura, prima del calcolo.
  - Rimanda a replay/run_lookup_rule.json (43785c4b…), che non è stato toccato.
- Script nuovo: replay/lookup_rule_al_addendum.py. Le funzioni sono copiate testualmente da lookup_rule_al.py.
- Metodo identico al file di run principale.
- **Verifiche (assert superate).**
  - Le colonne (a), (b), (d), (c) riproducono bit per bit gli AL di lookup_rule_al (oracolo e regola) e di ceiling_installed_cfg (oracolo).
  - I ρ\* di (c) e (d) contro (a) coincidono con la run principale.
  - Lookup rigenerato: 0 discrepanze rispetto alle tracce.

**Colonna (a′) = `--spec 4 --lookup-chain 2`.** Ho verificato il codice @7dd5cf1:
- generate.cpp L3208-3211: mtp_max_t=4 e spec=6.
- L3215-3218: con chain_base=6, spec = max(6, min(max(6,4)+2, 8)) = 8.
- S_mtp=4, quindi 3 draft MTP (L11173-11174).
- `sfx.propose(S−1)`, quindi lookup autonomo ≤7 token (L14897).
- **Non modellato:** il lookup *concatenato* dopo i draft MTP (blocco --lookup-chain, L14904-14920). Nel file di addendum ho scritto per errore L14905-14921: le righe corrette sono L14904-14920. (a′) è quindi MTP 3 + lookup autonomo ≤7, come l'ha definita il Lead.

## C. Colonna (a′): AL e scomposizione del guadagno di (b) su (a)

| insieme | AL (a) oracolo / con gate / senza gate | AL (a′) oracolo / con gate / senza gate | AL (b) oracolo / con gate / senza gate | quota regola/oracolo in (a′), con gate / senza gate | round con lookup in (a′), con gate / senza gate (token medi) |
|---|---|---|---|---|---|
| tune code | 5,025 / 4,884 / 4,770 | 6,045 / 5,787 / 5,575 | 6,709 / 6,230 / 6,105 | 95,7% / 92,2% | 61,6% (7,44) / 65,3% (6,89) |
| holdout code | 5,073 / 4,885 / 4,852 | 6,213 / 5,914 / 5,856 | 6,831 / 6,357 / 6,300 | 95,2% / 94,3% | 64,8% (7,45) / 67,8% (7,15) |
| tune chat | 2,585 / 2,003 / 1,981 | 2,590 / 2,010 / 1,987 | 2,893 / 2,138 / 2,116 | 77,6% / 76,7% | 3,2% (3,95) / 4,3% (3,11) |
| holdout chat | 2,782 / 2,282 / 2,233 | 2,789 / 2,286 / 2,237 | 3,290 / 2,529 / 2,492 | 82,0% / 80,2% | 5,6% (3,56) / 9,0% (2,60) |
| tune edit | 4,689 / 4,414 / 4,354 | 5,401 / 5,059 / 5,000 | 5,981 / 5,289 / 5,289 | 93,7% / 92,6% | 53,4% (7,21) / 57,0% (6,78) |
| holdout edit | 4,848 / 4,632 / 4,472 | 5,720 / 5,430 / 5,299 | 6,436 / 5,890 / 5,763 | 94,9% / 92,7% | 60,3% (7,12) / 64,5% (6,65) |

**Scomposizione.** Δ totale = (b)/(a)−1; solo lookup = (a′)/(a)−1; MTP più largo = (b)/(a′)−1. Le quote sono calcolate sul guadagno di AL (b)−(a). Tutti i valori hanno l'[IC95].

| insieme | serie | Δ totale (b) vs (a) | solo lookup (a′) vs (a) | MTP più largo (b) vs (a′) | quota lookup | quota MTP |
|---|---|---|---|---|---|---|
| tune code | oracolo | +33,5% [+29,2;+37,8] | +20,3% [+16,7;+24,7] | +11,0% [+6,0;+15,7] | 60,6% [48,5;75,5] | 39,4% [24,5;51,5] |
| tune code | regola con gate | +27,6% [+22,5;+31,5] | +18,5% [+14,7;+22,8] | +7,7% [+2,7;+12,4] | 67,1% [51,5;86,8] | 32,9% [13,2;48,5] |
| tune code | regola senza gate | +28,0% [+22,6;+32,2] | +16,9% [+13,1;+21,3] | +9,5% [+3,5;+15,2] | 60,3% [44,1;82,9] | 39,7% [17,1;55,9] |
| holdout code | oracolo | +34,7% [+31,7;+37,5] | +22,5% [+19,3;+25,8] | +10,0% [+6,7;+13,7] | 64,8% [54,7;74,9] | 35,2% [25,1;45,3] |
| holdout code | regola con gate | +30,1% [+27,6;+32,7] | +21,1% [+18,0;+24,4] | +7,5% [+4,1;+11,1] | 69,9% [58,3;82,5] | 30,1% [17,5;41,7] |
| holdout code | regola senza gate | +29,9% [+27,4;+32,3] | +20,7% [+17,4;+24,4] | +7,6% [+4,3;+11,1] | 69,3% [57,9;81,6] | 30,7% [18,4;42,1] |
| tune chat | oracolo | +11,9% [+6,0;+21,4] | +0,2% [+0,0;+0,6] | +11,7% [+5,5;+21,3] | 1,8% [0,0;8,3] | 98,2% [91,7;100,0] |
| tune chat | regola con gate | +6,7% [+2,5;+14,7] | +0,3% [+0,0;+0,8] | +6,4% [+2,2;+14,4] | 4,8% [0,0;14,7] | 95,2% [85,3;100,0] |
| tune chat | regola senza gate | +6,8% [+2,6;+14,6] | +0,3% [+0,0;+0,8] | +6,5% [+2,3;+14,2] | 4,7% [0,0;14,3] | 95,3% [85,7;100,0] |
| holdout chat | oracolo | +18,3% [+13,6;+24,5] | +0,2% [+0,0;+0,5] | +18,0% [+13,4;+24,2] | 1,3% [0,0;2,9] | 98,7% [97,1;100,0] |
| holdout chat | regola con gate | +10,8% [+7,3;+15,6] | +0,2% [+0,0;+0,4] | +10,6% [+7,2;+15,3] | 1,7% [0,0;3,8] | 98,3% [96,2;100,0] |
| holdout chat | regola senza gate | +11,6% [+7,7;+17,1] | +0,2% [+0,0;+0,4] | +11,4% [+7,6;+16,8] | 1,6% [0,0;3,6] | 98,4% [96,4;100,0] |
| tune edit | oracolo | +27,6% [+22,4;+34,7] | +15,2% [+8,3;+25,0] | +10,7% [+6,7;+13,8] | 55,1% [35,8;74,6] | 44,9% [25,4;64,2] |
| tune edit | regola con gate | +19,8% [+13,8;+28,9] | +14,6% [+8,0;+24,9] | +4,5% [+1,6;+6,8] | 73,7% [55,8;92,3] | 26,3% [7,7;44,2] |
| tune edit | regola senza gate | +21,5% [+13,9;+33,0] | +14,8% [+7,9;+25,4] | +5,8% [+3,3;+8,8] | 69,1% [53,2;84,0] | 30,9% [16,0;46,8] |
| holdout edit | oracolo | +32,8% [+28,6;+37,0] | +18,0% [+13,7;+22,8] | +12,5% [+8,7;+16,8] | 54,9% [43,0;67,2] | 45,1% [32,8;57,0] |
| holdout edit | regola con gate | +27,2% [+22,7;+31,8] | +17,2% [+12,7;+22,4] | +8,5% [+5,1;+12,1] | 63,4% [50,3;76,9] | 36,6% [23,1;49,7] |
| holdout edit | regola senza gate | +28,9% [+24,5;+33,9] | +18,5% [+13,3;+24,7] | +8,8% [+5,6;+12,1] | 64,1% [50,8;76,8] | 35,9% [23,2;49,2] |

Lettura:
- **Code ed edit.** Il guadagno di (b) su (a) viene per circa il 55–74% dal solo lookup ≤7. Il restante 26–45% viene dall'MTP più largo.
- **Chat.** Il guadagno viene quasi tutto dall'MTP più largo (95–99%).
- In tutti i casi è un dato di AL, non di tok/s.

## D. Rapporti di pareggio: PARAMETRICI, non misurati
**Modello.**
- s(T) = 1+ρ(T−1), con T = 1 + token proposti nel round (righe di verify effettive). Draft MTP e lookup sono a costo zero.
- Metro: Σ(a+1)/Σ s(T). ρ\* è il valore sopra il quale la colonna smette di battere la base. Il confronto è omogeneo (oracolo con oracolo, regola con regola).
- Calcolo: griglia [0,2] con passo 0,0005 più bisezione, verificato con la forma chiusa.
- I rapporti si ottengono da ρ\*:
  - s(16)/s(8) = (1+15ρ\*)/(1+7ρ\*), per la colonna (c);
  - s(12)/s(8) = (1+11ρ\*)/(1+7ρ\*), per la colonna (d).
- IC95 bootstrap sulle richieste (B=2000). Il rapporto cresce con ρ\*, quindi il suo IC si ricava dagli estremi dell'IC di ρ\*.
- **Convenzioni.**
  - "mai": la colonna non batte la base già a ρ=0 (stesso numero di round o più).
  - Un estremo "mai" nell'IC vuol dire che oltre il 2,5% delle repliche è "mai" (rapporto 1).
  - ">2": oltre il 2,5% delle repliche non pareggia entro ρ≤2. Corrisponde a s(16)/s(8) > 31/15 ≈ 2,067 e s(12)/s(8) > 23/15 ≈ 1,533.
  - Nel json quei percentili compaiono come NaN (percentile con +∞): vanno letti come ">2".
- **Tetti del modello lineare.** Il modello limita i rapporti a s(16)/s(8) < 15/7 ≈ 2,143 e s(12)/s(8) < 11/7 ≈ 1,571.

**Perché la forma lineare conta.** Il rapporto di pareggio dipende dalla forma lineare assunta per s(T). Su AMD va confrontato con l'intero profilo s(T) misurato, non solo con i due estremi s(8) e s(16): i round usano T variabili (1..16) e il metro somma s(T) su tutti i round.

### D1. (c) e (d) contro (b) T≤8: ρ\* [IC95] → rapporto [IC95]

| insieme | serie | (c) 16 vs (b): ρ\* → s(16)/s(8) | (d) 12 vs (b): ρ\* → s(12)/s(8) |
|---|---|---|---|
| tune code | oracolo | 0,411 [0,267;0,631] → s16/s8 1,848 [1,744;1,932] | 0,612 [0,377;1,321] → s12/s8 1,463 [1,415;1,516] |
| tune code | regola con gate | 0,559 [0,374;0,872] → s16/s8 1,910 [1,827;1,982] | 0,587 [0,316;1,473] → s12/s8 1,460 [1,394;1,521] |
| tune code | regola senza gate | 0,611 [0,407;1,015] → s16/s8 1,926 [1,846;2,002] | 0,407 [0,204;1,082] → s12/s8 1,423 [1,336;1,505] |
| holdout code | oracolo | 0,749 [0,587;0,981] → s16/s8 1,960 [1,919;1,998] | 0,853 [0,670;1,140] → s12/s8 1,489 [1,471;1,508] |
| holdout code | regola con gate | 0,583 [0,452;0,775] → s16/s8 1,918 [1,868;1,965] | 0,588 [0,439;0,808] → s12/s8 1,460 [1,431;1,486] |
| holdout code | regola senza gate | 0,501 [0,389;0,676] → s16/s8 1,889 [1,836;1,943] | 0,517 [0,400;0,671] → s12/s8 1,448 [1,421;1,471] |
| tune chat | oracolo | 0,065 [mai;0,500] → s16/s8 1,356 [1,000 (mai);1,889] | 0,091 [mai;>2] → s12/s8 1,222 [1,000 (mai);>1,533] |
| tune chat | regola con gate | 0,041 [mai;0,114] → s16/s8 1,254 [1,000 (mai);1,508] | 0,095 [mai;0,571] → s12/s8 1,229 [1,000 (mai);1,457] |
| tune chat | regola senza gate | 0,021 [mai;0,065] → s16/s8 1,148 [1,000 (mai);1,356] | 0,039 [mai;0,148] → s12/s8 1,123 [1,000 (mai);1,291] |
| holdout chat | oracolo | mai | mai |
| holdout chat | regola con gate | mai | mai |
| holdout chat | regola senza gate | mai | mai |
| tune edit | oracolo | 1,933 [1,120;>2] → s16/s8 2,064 [2,014;>2,067] | 1,024 [0,714;>2] → s12/s8 1,501 [1,476;>1,533] |
| tune edit | regola con gate | 0,581 [0,270;1,400] → s16/s8 1,917 [1,747;2,037] | 0,517 [0,283;1,018] → s12/s8 1,448 [1,380;1,501] |
| tune edit | regola senza gate | 0,232 [0,132;0,450] → s16/s8 1,708 [1,549;1,868] | 0,273 [0,175;0,415] → s12/s8 1,375 [1,315;1,425] |
| holdout edit | oracolo | 0,491 [0,313;0,753] → s16/s8 1,885 [1,785;1,961] | 0,454 [0,290;0,695] → s12/s8 1,435 [1,383;1,474] |
| holdout edit | regola con gate | 0,459 [0,282;0,745] → s16/s8 1,872 [1,759;1,959] | 0,317 [0,209;0,496] → s12/s8 1,394 [1,340;1,444] |
| holdout edit | regola senza gate | 0,372 [0,236;0,645] → s16/s8 1,826 [1,712;1,936] | 0,332 [0,205;0,579] → s12/s8 1,399 [1,337;1,458] |

### D2. (c) e (d) contro (a) installata: ρ\* [IC95] → rapporto [IC95]

| insieme | serie | (c) 16: ρ\* → s(16)/s(8) | (d) 12: ρ\* → s(12)/s(8) |
|---|---|---|---|
| tune code | oracolo | 0,394 [0,293;0,554] → s16/s8 1,839 [1,769;1,908] | 0,447 [0,334;0,656] → s12/s8 1,433 [1,400;1,469] |
| tune code | regola con gate | 0,516 [0,396;0,696] → s16/s8 1,895 [1,840;1,948] | 0,521 [0,404;0,710] → s12/s8 1,448 [1,422;1,476] |
| tune code | regola senza gate | 0,552 [0,430;0,725] → s16/s8 1,908 [1,858;1,955] | 0,451 [0,317;0,683] → s12/s8 1,434 [1,394;1,473] |
| holdout code | oracolo | 0,535 [0,423;0,674] → s16/s8 1,902 [1,854;1,943] | 0,529 [0,415;0,663] → s12/s8 1,450 [1,425;1,470] |
| holdout code | regola con gate | 0,670 [0,556;0,822] → s16/s8 1,942 [1,909;1,974] | 0,692 [0,599;0,796] → s12/s8 1,474 [1,461;1,484] |
| holdout code | regola senza gate | 0,637 [0,520;0,788] → s16/s8 1,934 [1,897;1,967] | 0,681 [0,589;0,792] → s12/s8 1,472 [1,460;1,484] |
| tune chat | oracolo | 0,049 [0,026;0,086] → s16/s8 1,293 [1,176;1,431] | 0,049 [0,026;0,087] → s12/s8 1,147 [1,088;1,216] |
| tune chat | regola con gate | 0,266 [0,159;0,536] → s16/s8 1,744 [1,602;1,902] | 0,325 [0,200;0,667] → s12/s8 1,397 [1,333;1,471] |
| tune chat | regola senza gate | 0,200 [0,130;0,349] → s16/s8 1,667 [1,544;1,811] | 0,251 [0,165;0,427] → s12/s8 1,364 [1,306;1,428] |
| holdout chat | oracolo | 0,077 [0,057;0,105] → s16/s8 1,400 [1,327;1,483] | 0,078 [0,058;0,106] → s12/s8 1,202 [1,165;1,243] |
| holdout chat | regola con gate | 0,231 [0,173;0,319] → s16/s8 1,707 [1,625;1,789] | 0,269 [0,203;0,362] → s12/s8 1,373 [1,336;1,410] |
| holdout chat | regola senza gate | 0,209 [0,141;0,376] → s16/s8 1,679 [1,567;1,828] | 0,268 [0,180;0,493] → s12/s8 1,373 [1,319;1,443] |
| tune edit | oracolo | 0,382 [0,205;0,873] → s16/s8 1,832 [1,673;1,982] | 0,321 [0,176;0,782] → s12/s8 1,395 [1,316;1,483] |
| tune edit | regola con gate | 0,482 [0,250;0,922] → s16/s8 1,882 [1,727;1,990] | 0,448 [0,258;0,797] → s12/s8 1,433 [1,368;1,485] |
| tune edit | regola senza gate | 0,297 [0,170;0,552] → s16/s8 1,771 [1,622;1,908] | 0,341 [0,199;0,591] → s12/s8 1,403 [1,333;1,460] |
| holdout edit | oracolo | 0,371 [0,256;0,563] → s16/s8 1,825 [1,733;1,912] | 0,349 [0,242;0,522] → s12/s8 1,405 [1,359;1,449] |
| holdout edit | regola con gate | 0,475 [0,332;0,671] → s16/s8 1,879 [1,799;1,942] | 0,402 [0,305;0,540] → s12/s8 1,422 [1,389;1,452] |
| holdout edit | regola senza gate | 0,482 [0,334;0,759] → s16/s8 1,882 [1,801;1,962] | 0,479 [0,351;0,706] → s12/s8 1,440 [1,406;1,475] |

### D2. (c) e (d) contro (a′) = --spec 4 --lookup-chain 2: ρ\* [IC95] → rapporto [IC95]

| insieme | serie | (c) 16: ρ\* → s(16)/s(8) | (d) 12: ρ\* → s(12)/s(8) |
|---|---|---|---|
| tune code | oracolo | 0,304 [0,216;0,462] → s16/s8 1,777 [1,688;1,873] | 0,333 [0,235;0,563] → s12/s8 1,400 [1,355;1,456] |
| tune code | regola con gate | 0,467 [0,356;0,679] → s16/s8 1,875 [1,815;1,944] | 0,463 [0,344;0,712] → s12/s8 1,437 [1,404;1,476] |
| tune code | regola senza gate | 0,654 [0,461;1,133] → s16/s8 1,938 [1,873;2,015] | 0,481 [0,326;0,857] → s12/s8 1,441 [1,397;1,490] |
| holdout code | oracolo | 0,429 [0,319;0,587] → s16/s8 1,857 [1,789;1,919] | 0,400 [0,295;0,550] → s12/s8 1,421 [1,385;1,454] |
| holdout code | regola con gate | 0,606 [0,454;0,838] → s16/s8 1,925 [1,869;1,976] | 0,619 [0,478;0,824] → s12/s8 1,464 [1,440;1,487] |
| holdout code | regola senza gate | 0,611 [0,472;0,793] → s16/s8 1,926 [1,877;1,968] | 0,673 [0,503;0,920] → s12/s8 1,471 [1,445;1,495] |
| tune chat | oracolo | 0,049 [0,025;0,088] → s16/s8 1,292 [1,168;1,434] | 0,049 [0,025;0,088] → s12/s8 1,146 [1,085;1,218] |
| tune chat | regola con gate | 0,320 [0,170;0,897] → s16/s8 1,790 [1,622;1,986] | 0,415 [0,223;1,327] → s12/s8 1,425 [1,348;1,516] |
| tune chat | regola senza gate | 0,241 [0,142;0,513] → s16/s8 1,717 [1,569;1,894] | 0,325 [0,189;0,729] → s12/s8 1,397 [1,325;1,478] |
| holdout chat | oracolo | 0,077 [0,057;0,106] → s16/s8 1,402 [1,327;1,487] | 0,078 [0,058;0,108] → s12/s8 1,202 [1,165;1,245] |
| holdout chat | regola con gate | 0,267 [0,199;0,364] → s16/s8 1,745 [1,665;1,821] | 0,320 [0,242;0,431] → s12/s8 1,395 [1,359;1,429] |
| holdout chat | regola senza gate | 0,267 [0,175;0,510] → s16/s8 1,745 [1,629;1,893] | 0,374 [0,240;0,801] → s12/s8 1,413 [1,358;1,485] |
| tune edit | oracolo | 0,339 [0,177;0,965] → s16/s8 1,804 [1,633;1,996] | 0,263 [0,147;0,767] → s12/s8 1,370 [1,290;1,482] |
| tune edit | regola con gate | 0,471 [0,225;1,080] → s16/s8 1,877 [1,699;2,009] | 0,416 [0,222;0,897] → s12/s8 1,425 [1,348;1,493] |
| tune edit | regola senza gate | 0,252 [0,145;0,516] → s16/s8 1,729 [1,576;1,895] | 0,294 [0,172;0,517] → s12/s8 1,385 [1,312;1,448] |
| holdout edit | oracolo | 0,304 [0,206;0,487] → s16/s8 1,778 [1,675;1,884] | 0,267 [0,184;0,419] → s12/s8 1,372 [1,322;1,426] |
| holdout edit | regola con gate | 0,454 [0,298;0,703] → s16/s8 1,869 [1,772;1,950] | 0,347 [0,254;0,493] → s12/s8 1,405 [1,366;1,443] |
| holdout edit | regola senza gate | 0,425 [0,293;0,667] → s16/s8 1,855 [1,769;1,941] | 0,405 [0,289;0,626] → s12/s8 1,422 [1,382;1,465] |

**Lettura di D1, che resta un modello parametrico.**
- **Code ed edit, contro T≤8:**
  - per la regola, s(16)/s(8) di pareggio vale tra 1,71 e 1,93 e s(12)/s(8) tra 1,38 e 1,46;
  - per l'oracolo, s(16)/s(8) vale tra 1,85 e 2,06 e s(12)/s(8) tra 1,43 e 1,50.
- **Chat, contro T≤8:**
  - holdout: "mai", in tutte le serie;
  - tune: rapporti bassi (1,12–1,36), con un IC che include "mai".
- **Contesto (Scout, @7dd5cf1).**
  - tune_knobs.py L170 scarta --spec ≥6 con il motivo "wider speculative windows were 4% to 16% slower". Hardware e dominio non sono dichiarati.
  - --spec installato = 4 (setup.py L9420); tune-values.ts L16 è solo un commento.
- **Cautela del Lead:** "l'AL per verifica non è il metro; un match lungo oggi viene consumato in due round da 8; il dato che decide è s(16) contro 2·s(8) su AMD."

## Limiti
- **Proxy 2B.** Accettazioni MTP, mtp_p e riferimento vengono dal proxy llama.cpp 2B ("proxy CPU, non AMD").
- **Uscite brevi.** Al massimo 128 token.
- **Copia dal prompt.** In code ed edit ce n'è molta.
- **Limiti del motore.** kVerifyMaxT=8 e kMaxT=8 nel motore: (d) e (c) richiedono di modificare i kernel e la policy.
- **(a′)** non modella il lookup concatenato.
- **Pareggi parametrici.** s(T) è lineare, i draft sono a costo zero, e non si tratta di tok/s né di un dato misurato.
- **Fuori dal modello.** La prima finestra e la DraftPolicy non sono modellate. Nell'oracolo T è la proposta completa della fonte vincente.
- **Non calcolato altro.** In particolare, il replay allineato alla run live di Bench è in attesa dei metadati.
