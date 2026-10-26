# Regola min(match,16) contro l'oracolo: (a) installata, (b) T≤8, (d) 12, (c) 16. Solo AL, descrittivo; ρ* PARAMETRICO

## Riferimenti
- File di run: replay/run_lookup_rule.json, sha256 43785c4ba35f44a3824064ce972b4eaba48ffaa68adede7a847ea7df070daec2.
  - Scritto alle 07:00:30 CET e messo in sola lettura prima di qualunque calcolo.
  - Contiene la regola, le precisazioni e le aggiunte A e B del Lead (06:59). Le aggiunte stanno nel file di run stesso, perché a quell'ora non era ancora scritto.
- Script: replay/lookup_rule_al.py. Lo script verifica lo sha del file di run e quello del json di ceiling_installed_cfg.
- Tracce: v1.1 tune e holdout, le stesse dei report precedenti (sha nel json).

**Regola del Lead (testo letterale).** "Quando c'è un match di lookup, la regola propone min(lunghezza del match, 16) token; altrimenti usa la policy attuale col default installato. Calcola l'AL reale accanto all'oracolo, nelle tre colonne: installata, T≤8 e 16." Con l'aggiunta A la colonna 12 si affianca alle altre.

## Implementazione (fissata nel file di run)
- **Lookup.**
  - È il SuffixDrafter di produzione (sd_scan, min_match 3, max_match 64, max_k 16), da zero per ogni richiesta su prompt+y[:i].
  - "Match" significa k16>0. La lunghezza è quella del candidato proposto, tagliata al tetto della colonna: L=min(k16, tetto). y non entra mai nella decisione.
  - Accettazione = lcp(proposta, y[i:]).
- **Ramo "altrimenti".** È l'MTP con --spec-min-p 0.5, come DefaultMinP di holdout_v11_speccost_vs_default.py (6809946d), senza la sua parte DraftPolicy.
  - T = min(S_mtp, 1+run), dove run è il numero di mtp_p iniziali ≥0,5 e S_mtp = draft MTP della colonna + 1.
  - a = min(mtp_acc, T−1).
- **Gate.** Nella variante con gate si usa il lookup solo se il primo token del candidato è uguale al primo draft MTP della traccia (drafts[0], come in generate.cpp L14899); altrimenti si usa il ramo MTP. Nella variante senza gate il lookup si usa ogni volta che k16>0.
- **Oracolo.** È esattamente il cammino di ceiling_installed_cfg. **Riproduce bit per bit** i suoi AL in tutti e 6 gli insiemi × 4 colonne (verifica con assert superata).
- **Controllo sul lookup rigenerato.** min(acc16,7) = lk_acc delle tracce: 0 discrepanze.
- **Statistica.** Bootstrap B=2000, seed 0, sulle richieste (sessioni).
- **Cosa non è modellato.** La prima finestra (L14889) e la DraftPolicy.

## 1. AL: regola (con e senza gate), oracolo e quota regola/oracolo, per colonna

**(a) installata: MTP 3, lookup ≤5**

| insieme | AL oracolo | AL regola con gate [IC95] | AL regola senza gate [IC95] | quota con gate [IC95] | quota senza gate [IC95] |
|---|---|---|---|---|---|
| tune code | 5,025 | 4,884 [4,59;5,20] | 4,770 [4,47;5,11] | 97,2% [95,1;99,2] | 94,9% [92,3;97,4] |
| holdout code | 5,073 | 4,885 [4,60;5,16] | 4,852 [4,57;5,14] | 96,3% [94,4;98,0] | 95,6% [93,6;97,7] |
| tune chat | 2,585 | 2,003 [1,68;2,47] | 1,981 [1,67;2,42] | 77,5% [72,2;84,5] | 76,6% [71,7;82,9] |
| holdout chat | 2,782 | 2,282 [2,07;2,55] | 2,233 [2,03;2,49] | 82,0% [79,4;84,9] | 80,2% [77,7;83,0] |
| tune edit | 4,689 | 4,414 [3,63;5,45] | 4,354 [3,63;5,29] | 94,1% [90,3;99,2] | 92,9% [90,1;96,7] |
| holdout edit | 4,848 | 4,632 [4,23;5,07] | 4,472 [4,09;4,88] | 95,6% [94,1;97,0] | 92,3% [90,3;94,3] |

**(b) T≤8: MTP 7, lookup ≤7**

| insieme | AL oracolo | AL regola con gate [IC95] | AL regola senza gate [IC95] | quota con gate [IC95] | quota senza gate [IC95] |
|---|---|---|---|---|---|
| tune code | 6,709 | 6,230 [5,87;6,67] | 6,105 [5,78;6,50] | 92,9% [90,3;95,5] | 91,0% [88,5;93,7] |
| holdout code | 6,831 | 6,357 [5,94;6,76] | 6,300 [5,88;6,72] | 93,0% [90,6;95,5] | 92,2% [89,8;94,7] |
| tune chat | 2,893 | 2,138 [1,73;2,81] | 2,116 [1,72;2,75] | 73,9% [69,8;80,3] | 73,2% [69,5;78,7] |
| holdout chat | 3,290 | 2,529 [2,23;2,92] | 2,492 [2,20;2,87] | 76,9% [74,4;79,8] | 75,8% [73,3;78,7] |
| tune edit | 5,981 | 5,289 [4,13;6,99] | 5,289 [4,14;6,99] | 88,4% [83,9;95,0] | 88,4% [83,9;95,0] |
| holdout edit | 6,436 | 5,890 [5,22;6,64] | 5,763 [5,13;6,47] | 91,5% [88,9;94,2] | 89,6% [86,8;92,5] |

**(d) 12: MTP 7, lookup ≤12**

| insieme | AL oracolo | AL regola con gate [IC95] | AL regola senza gate [IC95] | quota con gate [IC95] | quota senza gate [IC95] |
|---|---|---|---|---|---|
| tune code | 8,660 | 8,195 [7,35;9,25] | 7,929 [7,12;9,01] | 94,6% [91,2;98,5] | 91,6% [87,1;95,9] |
| holdout code | 9,051 | 8,274 [7,45;9,17] | 8,293 [7,45;9,26] | 91,4% [89,0;93,8] | 91,6% [89,0;94,5] |
| tune chat | 2,899 | 2,146 [1,73;2,83] | 2,123 [1,73;2,77] | 74,0% [69,8;80,5] | 73,2% [69,5;78,8] |
| holdout chat | 3,290 | 2,529 [2,23;2,92] | 2,492 [2,20;2,87] | 76,9% [74,4;79,8] | 75,8% [73,3;78,7] |
| tune edit | 7,485 | 6,531 [4,69;10,16] | 6,368 [4,64;9,70] | 87,2% [83,3;94,5] | 85,1% [82,2;90,0] |
| holdout edit | 7,983 | 7,257 [6,11;8,67] | 7,229 [6,09;8,65] | 90,9% [88,6;93,5] | 90,6% [88,0;93,7] |

**(c) 16: MTP 7, lookup ≤16**

| insieme | AL oracolo | AL regola con gate [IC95] | AL regola senza gate [IC95] | quota con gate [IC95] | quota senza gate [IC95] |
|---|---|---|---|---|---|
| tune code | 9,847 | 9,112 [8,07;10,53] | 9,112 [8,00;10,62] | 92,5% [86,7;97,5] | 92,5% [87,7;96,9] |
| holdout code | 10,397 | 9,434 [8,32;10,78] | 9,434 [8,27;10,84] | 90,7% [87,9;93,8] | 90,7% [87,8;94,1] |
| tune chat | 2,906 | 2,146 [1,73;2,83] | 2,123 [1,73;2,77] | 73,8% [69,7;80,2] | 73,1% [69,4;78,6] |
| holdout chat | 3,290 | 2,529 [2,23;2,92] | 2,492 [2,20;2,87] | 76,9% [74,4;79,8] | 75,8% [73,3;78,7] |
| tune edit | 8,205 | 7,072 [4,92;11,74] | 6,882 [4,83;11,13] | 86,2% [82,2;93,3] | 83,9% [80,0;90,7] |
| holdout edit | 8,998 | 8,319 [6,73;10,36] | 8,210 [6,66;10,24] | 92,5% [89,8;95,7] | 91,2% [88,2;95,0] |

## 2. ΔAL della regola fra le colonne, con [IC95]

| insieme | variante | (b) vs (a) | (d) vs (a) | (c) vs (a) | (c) vs (b) | (d) vs (b) |
|---|---|---|---|---|---|---|
| tune code | con gate | +27,6% [+22,5;+31,5] | +67,8% [+59,6;+78,6] | +86,6% [+74,8;+103,4] | +46,3% [+36,1;+59,5] | +31,5% [+23,6;+40,5] |
| tune code | senza gate | +28,0% [+22,6;+32,2] | +66,2% [+57,9;+77,4] | +91,0% [+77,0;+109,9] | +49,3% [+37,0;+64,9] | +29,9% [+22,0;+39,7] |
| holdout code | con gate | +30,1% [+27,6;+32,7] | +69,4% [+61,3;+78,1] | +93,1% [+79,5;+109,5] | +48,4% [+38,9;+59,8] | +30,2% [+24,6;+36,5] |
| holdout code | senza gate | +29,9% [+27,4;+32,3] | +70,9% [+62,5;+80,6] | +94,4% [+80,4;+111,8] | +49,7% [+39,8;+61,9] | +31,6% [+25,9;+38,2] |
| tune chat | con gate | +6,7% [+2,5;+14,7] | +7,1% [+2,8;+15,2] | +7,1% [+2,8;+15,2] | +0,3% [+0,0;+0,8] | +0,3% [+0,0;+0,8] |
| tune chat | senza gate | +6,8% [+2,6;+14,6] | +7,2% [+2,9;+15,2] | +7,2% [+2,9;+15,2] | +0,3% [+0,0;+0,8] | +0,3% [+0,0;+0,8] |
| holdout chat | con gate | +10,8% [+7,3;+15,6] | +10,8% [+7,3;+15,6] | +10,8% [+7,3;+15,6] | +0,0% [+0,0;+0,0] | +0,0% [+0,0;+0,0] |
| holdout chat | senza gate | +11,6% [+7,7;+17,1] | +11,6% [+7,7;+17,1] | +11,6% [+7,7;+17,1] | +0,0% [+0,0;+0,0] | +0,0% [+0,0;+0,0] |
| tune edit | con gate | +19,8% [+13,8;+28,9] | +48,0% [+28,1;+85,8] | +60,2% [+34,0;+116,4] | +33,7% [+17,7;+68,5] | +23,5% [+12,2;+45,4] |
| tune edit | senza gate | +21,5% [+13,9;+33,0] | +46,3% [+27,0;+82,3] | +58,1% [+32,3;+110,5] | +30,1% [+15,8;+59,8] | +20,4% [+11,1;+37,4] |
| holdout edit | con gate | +27,2% [+22,7;+31,8] | +56,7% [+44,5;+71,5] | +79,6% [+58,9;+105,9] | +41,2% [+28,9;+57,6] | +23,2% [+16,5;+31,6] |
| holdout edit | senza gate | +28,9% [+24,5;+33,9] | +61,7% [+48,7;+77,5] | +83,6% [+62,4;+111,7] | +42,5% [+29,7;+59,8] | +25,4% [+18,1;+34,9] |

## 3. Quando la regola sceglie il lookup
- Le colonne della tabella danno, per ciascuna colonna (a)/(b)/(d)/(c), la quota dei round del cammino in cui la regola prende il ramo lookup, e tra parentesi i token medi per round (a+1) in quei round.
- "Posizioni con match" = posizioni teacher-forced con k16>0, e con k16>0 più gate superato.

| insieme | posizioni con match / con match e gate | con gate: (a) / (b) / (d) / (c) | senza gate: (a) / (b) / (d) / (c) |
|---|---|---|---|
| tune code | 83,5% / 79,3% | 68,4% (5,68) / 62,8% (7,44) / 53,0% (11,68) / 46,3% (15,00) | 70,3% (5,47) / 66,5% (7,05) / 56,5% (10,78) / 50,0% (14,00) |
| holdout code | 85,2% / 81,8% | 70,4% (5,66) / 65,8% (7,45) / 55,0% (11,57) / 49,7% (14,74) | 73,3% (5,48) / 68,7% (7,21) / 58,8% (11,09) / 53,2% (13,96) |
| tune chat | 10,7% / 6,5% | 3,4% (3,57) / 1,6% (4,67) / 1,2% (6,00) / 1,2% (6,00) | 4,6% (2,90) / 3,1% (3,11) / 2,7% (3,50) / 2,7% (3,50) |
| holdout chat | 15,6% / 9,6% | 5,8% (3,46) / 3,9% (3,98) / 3,9% (3,98) / 3,9% (3,98) | 9,2% (2,55) / 6,0% (3,01) / 6,0% (3,01) / 6,0% (3,01) |
| tune edit | 82,0% / 77,0% | 59,7% (5,64) / 53,3% (7,26) / 41,8% (11,10) / 36,5% (13,71) | 62,6% (5,38) / 56,2% (6,95) / 47,3% (9,95) / 43,0% (11,81) |
| holdout edit | 84,8% / 79,0% | 64,8% (5,58) / 60,9% (7,18) / 50,9% (10,42) / 47,0% (13,37) | 70,1% (5,16) / 65,6% (6,80) / 56,8% (9,84) / 51,0% (12,46) |

Nota: in code la regola con gate e quella senza gate in (c) danno lo stesso AL (stesso numero di round: 134 nel tune, 378 nell'holdout), ma con righe di verify diverse. È un dato osservato, non un errore di calcolo: i due cammini sono distinti.

## 4. ρ di pareggio: PARAMETRICO, non misurato
- **Metro.** M(ρ) = Σ(a+1) / Σ s(T), con s(T) = 1+ρ(T−1) e T = 1 + token proposti nel round (righe di verify effettive). Draft MTP e lookup sono a costo zero.
- **ρ\*.** È il valore di ρ sopra il quale la colonna smette di battere (a) nel metro. Il confronto è omogeneo: oracolo contro oracolo (a), regola con gate contro regola con gate (a), regola senza gate contro regola senza gate (a).
  - Calcolo: griglia [0,2] con passo 0,0005, poi bisezione; verificato con la forma chiusa (il metro è lineare in ρ, ρ\* = ΔR/ΔX) e coincide.
  - IC95 bootstrap sulle richieste (B=2000). Il calcolo ha richiesto pochi secondi, quindi l'IC è riportato.
  - Nessun punto risulta "mai" o ">2". Le eventuali repliche ">2" sono contate come +∞.
- In tabella: ρ\* [IC95]; tra parentesi s(16)/s(1) = 1+15ρ\* e s(8)/s(1) = 1+7ρ\*.

| insieme | serie | (b) T≤8 | (d) 12 | (c) 16 |
|---|---|---|---|---|
| tune code | oracolo | 0,379 [0,279;0,569] (6,68; 3,65) | 0,447 [0,334;0,656] (7,71; 4,13) | 0,394 [0,293;0,554] (6,91; 3,76) |
| tune code | regola con gate | 0,474 [0,297;0,744] (8,11; 4,32) | 0,521 [0,404;0,710] (8,81; 4,64) | 0,516 [0,396;0,696] (8,73; 4,61) |
| tune code | regola senza gate | 0,496 [0,313;0,723] (8,43; 4,47) | 0,451 [0,317;0,683] (7,77; 4,16) | 0,552 [0,430;0,725] (9,28; 4,86) |
| holdout code | oracolo | 0,417 [0,306;0,574] (7,26; 3,92) | 0,529 [0,415;0,663] (8,94; 4,70) | 0,535 [0,423;0,674] (9,02; 4,74) |
| holdout code | regola con gate | 0,801 [0,647;1,000] (13,01; 6,61) | 0,692 [0,599;0,796] (11,38; 5,84) | 0,670 [0,556;0,822] (11,06; 5,69) |
| holdout code | regola senza gate | 0,914 [0,703;1,279] (14,70; 7,39) | 0,681 [0,589;0,792] (11,21; 5,77) | 0,637 [0,520;0,788] (10,56; 5,46) |
| tune chat | oracolo | 0,049 [0,025;0,088] (1,73; 1,34) | 0,049 [0,026;0,087] (1,74; 1,35) | 0,049 [0,026;0,086] (1,74; 1,35) |
| tune chat | regola con gate | 0,371 [0,233;0,750] (6,57; 3,60) | 0,325 [0,200;0,667] (5,88; 3,28) | 0,266 [0,159;0,536] (4,99; 2,86) |
| tune chat | regola senza gate | 0,345 [0,229;0,592] (6,17; 3,41) | 0,251 [0,165;0,427] (4,77; 2,76) | 0,200 [0,130;0,349] (4,00; 2,40) |
| holdout chat | oracolo | 0,079 [0,059;0,108] (2,19; 1,56) | 0,078 [0,058;0,106] (2,17; 1,55) | 0,077 [0,057;0,105] (2,15; 1,54) |
| holdout chat | regola con gate | 0,370 [0,285;0,481] (6,55; 3,59) | 0,269 [0,203;0,362] (5,03; 2,88) | 0,231 [0,173;0,319] (4,47; 2,62) |
| holdout chat | regola senza gate | 0,482 [0,312;1,105] (8,22; 4,37) (0,2% repliche >2) | 0,268 [0,180;0,493] (5,02; 2,88) | 0,209 [0,141;0,376] (4,14; 2,47) |
| tune edit | oracolo | 0,214 [0,123;0,606] (4,21; 2,50) | 0,321 [0,176;0,782] (5,81; 3,25) | 0,382 [0,205;0,873] (6,74; 3,68) |
| tune edit | regola con gate | 0,397 [0,231;0,722] (6,95; 3,78) | 0,448 [0,258;0,797] (7,71; 4,13) | 0,482 [0,250;0,922] (8,23; 4,38) |
| tune edit | regola senza gate | 0,423 [0,215;1,196] (7,34; 3,96) (0,4% repliche >2) | 0,341 [0,199;0,591] (6,11; 3,38) | 0,297 [0,170;0,552] (5,45; 3,08) |
| holdout edit | oracolo | 0,307 [0,207;0,485] (5,60; 3,15) | 0,349 [0,242;0,522] (6,23; 3,44) | 0,371 [0,256;0,563] (6,57; 3,60) |
| holdout edit | regola con gate | 0,494 [0,368;0,682] (8,41; 4,46) | 0,402 [0,305;0,540] (7,04; 3,82) | 0,475 [0,332;0,671] (8,13; 4,33) |
| holdout edit | regola senza gate | 0,696 [0,462;1,403] (11,44; 5,87) (0,4% repliche >2) | 0,479 [0,351;0,706] (8,19; 4,35) | 0,482 [0,334;0,759] (8,23; 4,38) |

**Contesto (Scout, @7dd5cf1).**
- tune_knobs.py L170 scarta --spec ≥6 con il motivo "wider speculative windows were 4% to 16% slower". Hardware e dominio non sono dichiarati.
- --spec installato = 4 (setup.py L9420, insieme a --spec-min-p 0.5).
- tune-values.ts L16 è solo un commento.

## Cautela del Lead
"l'AL per verifica non è il metro; un match lungo oggi viene consumato in due round da 8; il dato che decide è s(16) contro 2·s(8) su AMD."

Il rapporto di pareggio s(16)/s(8) non l'ho calcolato: è in attesa del sì del Lead.

## Limiti
- **Proxy 2B.** Accettazioni MTP, mtp_p e riferimento greedy vengono dal proxy llama.cpp 2B ("proxy CPU, non AMD").
- **Uscite brevi.** Al massimo 128 token, quindi le corse lunghe vengono tagliate dalla fine della risposta.
- **Copia dal prompt.** In code ed edit ce n'è molta; il lookup guadagna lì.
- **Limiti del motore.** Oggi kVerifyMaxT=8 e kMaxT=8: le colonne (d) e (c) richiedono di modificare i kernel di verify e la policy.
- **ρ\* parametrico.** s(T) è lineare, draft MTP e lookup sono a costo zero, e il metro non è un tok/s.
  - L'oracolo usa come T la proposta completa della fonte vincente.
  - Per questo il ρ\* dell'oracolo non è un tetto superiore del ρ\* della regola: per esempio, in chat il ramo MTP dell'oracolo usa sempre la catena intera, mentre la regola usa min_p.
- **Prima finestra e DraftPolicy** non sono modellate. La regola sostituisce la DraftPolicy (prende il lookup ogni volta che c'è un match, con gate se previsto).
- **Non calcolati:** il rapporto s(16)/s(8) di pareggio, il replay allineato alla run live di Bench (in attesa dei metadati) e le sorgenti terze.

## Addendum C e D
L'addendum C+D sta in results/v2/lookup_rule_al_addendum/: colonna (a′), scomposizione di (b)−(a) e rapporti di pareggio s(16)/s(8) e s(12)/s(8).
- È stato registrato prima del calcolo in replay/run_lookup_rule_addendum.json, sha256 f151f9852e0fd551c44ff3d13a864613006b75b901c1ac201f60268fbe370a64.
- Script nuovo: replay/lookup_rule_al_addendum.py.
- Questa cartella e questo json non sono stati toccati dall'addendum.
