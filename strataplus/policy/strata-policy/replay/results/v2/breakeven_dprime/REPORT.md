# Pareggio parametrico (d′) = MTP 3 draft + lookup ≤12 contro (a′) 3/7 e (a) 3/5: proxy CPU, AL, parametrico

## Riferimenti
- **Run file:** replay/run_breakeven_dprime.json, sha256 beacb25e7aebf01e83c790cb8aecb268eba82ab5ff2fe181dee62fdc60fd7e24.
  - Scritto alle 08:03:22 CET, in sola lettura, prima di aprire le tracce e di calcolare.
- **Script:** replay/breakeven_dprime.py.
  - Le funzioni prompts, walk_oracle, walk_rule, rho_star e fmt_rho sono copiate verbatim da lookup_rule_al_addendum.py (b402c026…); lo script verifica che il testo sia identico.
- **Tracce v1.1** (le stesse dell'addendum), verificate con assert:

  | traccia | sha256 |
  |---|---|
  | tune tf_d7_p30 | 87efe507… |
  | holdout code | a9e247b2… |
  | holdout chat | b5380c42… |
  | holdout edit | d9a48386… |

- **Lib, binding e dipendenze:** lib 8fb27b0d…, native.py 6bc1af8e…, postprocess.py 02811133….

## Bracci e convenzione delle righe

| braccio | draft MTP | lookup max | etichetta T | righe effettive max nel replay (MTP / lookup) |
|---|---|---|---|---|
| (a) installata, --spec 4 (spec effettivo 6 con suffix on, generate.cpp L3208-3211) | 3 | 5 | 6 | 4 / 6 |
| (a′) --spec 8 --mtp-max-t 4 | 3 | 7 | 8 | 4 / 8 |
| (d′) patch T=12 | 3 | 12 | 12 | 4 / 13 |

- **Convenzione per (d′):** la stessa di (d) 7/12 → s(12) nell'addendum. Il lookup a 12 token occupa fino a 13 righe effettive, ma l'etichetta è 12 (vedi anomalia 1).
- **Costo del round:** usa sempre le righe effettive, T = 1 + token proposti.
- **Modello:** s(T) = 1 + ρ(T−1), draft MTP e lookup a costo zero. Metro: Σ(a+1)/Σ s(T_round).
- **ρ\*:** il valore sopra il quale (d′) smette di battere la base. Griglia [0,2] + bisezione, IC95 bootstrap con B=2000 e seed 0 sulle richieste (stesse repliche dell'addendum).
- **Rapporto di pareggio:**
  - contro (a′): s(12)/s(8) = (1+11ρ\*)/(1+7ρ\*);
  - contro (a): s(12)/s(6) = (1+11ρ\*)/(1+5ρ\*).
  - Solo come lettura letterale di '--spec 4' riporto anche s(12)/s(4) = (1+11ρ\*)/(1+3ρ\*).
- **Rapporto massimo possibile per costruzione:**

  | rapporto | per ρ→∞ | a ρ=2, bordo della griglia |
  |---|---|---|
  | s(12)/s(8) | 11/7 ≈ 1,571 | 23/15 ≈ 1,533 |
  | s(12)/s(6) | 11/5 = 2,2 | 23/11 ≈ 2,091 |
  | s(12)/s(4) | 11/3 ≈ 3,667 | 23/7 ≈ 3,286 |

  Un rapporto AMD misurato sopra questi valori significa che, in questo modello, (d′) non conviene a nessun ρ ≤ 2.
- **Esistenza del pareggio:** esiste un ρ\* > 0 se e solo se (d′) fa meno round della base (batte la base a ρ=0) e propone più righe.
- **Lettura:** la decisione si basa sul tune; l'holdout è già stato usato ed è solo descrittivo, nessun parametro è scelto su di esso.

## Controlli di coerenza

Gli AL ricalcolati di (a), (a′) e (d), oracolo e regola con gate, coincidono **esattamente** (uguaglianza in virgola mobile e IC95) con lookup_rule_al.json (50f26aed…) e lookup_rule_al_addendum.json (07fa2bec…), su tutti e 6 gli insiemi. Discrepanze lookup16 contro le tracce (cap 7): 0 ovunque.

Valori attesi dal messaggio (holdout, regola con gate), riletti dal file:

| dominio | (a) | (a′) | (d) | atteso |
|---|---|---|---|---|
| code | 4,8849 | 5,9138 | 8,2738 | 4.88 / 5.91 / 8.27, confermato |
| edit | 4,6321 | 5,4298 | 7,2573 | 4.63 / 5.43 / 7.26, confermato |
| chat | 2,2815 | 2,2858 | 2,5288 | 2.28 / 2.29 / (non dato), confermato |

## AL di (d′) a confronto con (a) e (a′) (IC95)

| insieme | serie | (a) | (a′) | (d′) |
|---|---|---|---|---|
| tune code | oracolo | 5,025 | 6,045 | 7,631 [6,809;8,660] |
| tune code | regola con gate | 4,884 | 5,787 | 7,355 [6,393;8,538] |
| tune edit | oracolo | 4,689 | 5,401 | 6,737 [4,942;9,846] |
| tune edit | regola con gate | 4,414 | 5,059 | 6,154 [4,414;9,481] |
| tune chat | oracolo | 2,585 | 2,590 | 2,595 [2,323;2,967] |
| tune chat | regola con gate | 2,003 | 2,010 | 2,010 [1,682;2,481] |
| holdout code | oracolo | 5,073 | 6,213 | 8,068 [7,222;8,995] |
| holdout code | regola con gate | 4,885 | 5,914 | 7,685 [6,761;8,757] |
| holdout edit | oracolo | 4,848 | 5,720 | 7,229 [6,091;8,651] |
| holdout edit | regola con gate | 4,632 | 5,430 | 6,809 [5,653;8,286] |
| holdout chat | oracolo | 2,782 | 2,789 | 2,791 [2,597;3,030] |
| holdout chat | regola con gate | 2,282 | 2,286 | 2,286 [2,070;2,556] |

Cattura (gate/oracolo) e quota di round lookup per (d′) con gate:

| insieme | cattura | round lookup | token medi per round lookup |
|---|---|---|---|
| tune code | 96,4% [91,8;101,8] | 52,4% | 11,16 |
| tune edit | 91,3% [88,2;96,3] | 43,3% | 10,79 |
| tune chat | 77,4% [72,1;84,5] | 3,2% | 4,00 |
| holdout code | 95,3% [92,6;98,1] | 54,7% | 11,52 |
| holdout edit | 94,2% [92,5;96,2] | 50,8% | 10,66 |
| holdout chat | 81,9% [79,3;84,8] | 5,6% | 3,57 |

## Pareggi (PARAMETRICI, non misurati)

- Formato di ρ\*: punto [IC95].
- "mai": (d′) non batte la base nemmeno a ρ=0.

| insieme | serie | (d′) vs (a′): ρ\* | s(12)/s(8) | (d′) vs (a): ρ\* | s(12)/s(6) | s(12)/s(4), lettura letterale |
|---|---|---|---|---|---|---|
| tune code | oracolo | 0,627 [0,448;0,913] | 1,465 [1,433;1,494] | 0,741 [0,596;0,951] | 1,945 [1,898;1,992] | 2,839 [2,710;2,975] |
| tune code | regola con gate | 0,450 [0,252;0,909] | 1,434 [1,364;1,494] | 0,525 [0,360;0,773] | 1,869 [1,771;1,953] | 2,631 [2,384;2,863] |
| tune edit | oracolo | 0,553 [0,340;0,864] | 1,454 [1,402;1,490] | 0,546 [0,343;0,818] | 1,878 [1,758;1,964] | 2,656 [2,352;2,894] |
| tune edit | regola con gate | 0,405 [0,244;0,658] | 1,423 [1,361;1,470] | 0,446 [0,278;0,708] | 1,828 [1,698;1,936] | 2,526 [2,214;2,813] |
| tune chat | oracolo | 0,021 [mai;0,048] | 1,073 [1,000;1,143] | 0,033 [mai;0,068] | 1,171 [1,000;1,304] | 1,242 [1,000;1,451] |
| tune chat | regola con gate | mai [mai;0,000] | mai [1,000;1,000] | 0,016 [mai;0,039] | 1,091 [1,000;1,195] | 1,125 [1,000;1,278] |
| holdout code | oracolo | 0,687 [0,530;0,895] | 1,473 [1,450;1,493] | 0,801 [0,685;0,927] | 1,960 [1,929;1,987] | 2,883 [2,794;2,961] |
| holdout code | regola con gate | 0,594 [0,415;0,844] | 1,461 [1,425;1,489] | 0,686 [0,544;0,863] | 1,929 [1,878;1,974] | 2,794 [2,654;2,923] |
| holdout edit | oracolo | 0,469 [0,316;0,681] | 1,438 [1,394;1,472] | 0,546 [0,398;0,720] | 1,878 [1,799;1,939] | 2,656 [2,451;2,823] |
| holdout edit | regola con gate | 0,380 [0,258;0,606] | 1,415 [1,368;1,462] | 0,436 [0,311;0,634] | 1,823 [1,731;1,912] | 2,511 [2,288;2,747] |
| holdout chat | oracolo | 0,007 [mai;0,022] | 1,026 [1,000;1,075] | 0,020 [0,004;0,043] | 1,111 [1,025;1,212] | 1,153 [1,033;1,304] |
| holdout chat | regola con gate | mai [mai;0,000] | mai [1,000;1,000] | 0,008 [mai;0,022] | 1,047 [1,000;1,118] | 1,063 [1,000;1,163] |

Controllo: per ogni coppia il punto ρ\* coincide con la forma chiusa (R_base − R_d′)/(X_d′ − X_base). Round, righe e quote mai/>2 per replica sono nel json.

## Lettura (tune decisionale, holdout descrittivo)
- **Code ed edit:** il pareggio esiste in tutte le coppie e serie.
  - **Contro (a′), regola con gate, tune:** (d′) resta avanti finché il costo relativo AMD s(12)/s(8) è sotto 1,434 per code e 1,423 per edit. Il tetto per costruzione è 1,571.
  - **Contro (a), regola con gate, tune:** la soglia s(12)/s(6) è 1,869 per code e 1,828 per edit.
- **Chat, regola con gate, contro (a′):** il risultato è "mai" in tune e holdout.
  - (d′) fa esattamente gli stessi round di (a′): il guadagno di AL è zero (ΔR = 0).
  - (d′) però propone più righe in totale (ΔX = 90 in tune, 270 in holdout), quindi non esiste pareggio: con qualunque ρ > 0 costa di più di (a′).
- **Chat, oracolo:** ρ\* è piccolo, cioè il pareggio richiede un rapporto vicino a 1.
- I numeri non decidono quale braccio vince E-AMD-0: dipendono dal profilo s(T) misurato su AMD. Va confrontato con l'intero profilo (T variabile nei round), non solo con gli estremi; il pareggio lineare è un riassunto.

## Anomalie e limiti
1. **Convenzione delle righe ereditata da (d).** L'etichetta di (d′) è T=12, ma nel replay il lookup a 12 token occupa fino a 13 righe. Nel motore (sfx.propose(S−1), L14897) una finestra S=12 proporrebbe al massimo 11 token.
   - La patch T=12, se implementata come finestra di 12 righe, avrebbe lookup ≤11 e non ≤12 come qui.
   - Ho mantenuto la convenzione di (d) come richiesto, senza adattarla.
2. **T di (a).** Il messaggio chiama (a) '--spec 4'. Con suffix on, il motore porta spec a 6 (L3208-3211), che sono anche le righe effettive massime di (a) (lookup ≤5 → 6 righe; MTP 4 righe).
   - Il rapporto principale è quindi s(12)/s(6). Riporto s(12)/s(4) solo come lettura letterale, senza sceglierla.
3. **Lookup concatenato non modellato,** come in (a′) nell'addendum. La prima finestra (L14889) non è modellata.
4. **Limiti generali:**
   - proxy CPU, non AMD;
   - solo AL; il costo dei draft MTP e lookup è assunto zero;
   - modello lineare;
   - holdout già usato.
