# Oracolo contro la configurazione installata: (a) installata, (b) T≤8, (c) lookup16, (d) lookup12. Solo AL, descrittivo

**Cos'è.** Un tetto oracolo offline sull'AL. Non dà tok/s e non dice nulla sul costo.
- Script: replay/ceiling_installed_cfg.py. Il metodo è quello di ceiling_long_window.py (27995db9…, non modificato), senza sorgenti terze.
- Tracce v1.1: tune tf_d7_p30 e holdout code/chat/edit tf_d7, le stesse dei report precedenti (sha nel json).
- Oracolo per round: a = max(MTP, lookup) troncato a n−i−1; il round vale a+1 token. Nessuna memoria tra richieste.
- Lookup **rigenerato** con il SuffixDrafter di produzione (sd_scan nativo, min_match 3, max_match 64, max_k 16), da zero per ogni richiesta su prompt+y[:i].
- Accettazione = lcp(cand[:L], y[p:p+L]) = min(acc16, L).
- MTP preso dalle tracce (Dmax 7) e limitato al cap della configurazione.
- Bootstrap B=2000, seed 0, sulle richieste.

## Configurazioni (righe = finestra di verify T = 1 + draft; strata-src @7dd5cf18)

| col | MTP (draft) | lookup (token) | da dove viene |
|---|---|---|---|
| a | ≤3 (4 righe) | ≤5 (6 righe) | Vedi sotto |
| b | ≤7 | ≤7 | T≤8 di oggi (kVerifyMaxT=8, DraftPolicy::kMaxT=8) |
| c | ≤7 | ≤16 | ipotesi GPU |
| d | ≤7 | ≤12 | ipotesi GPU |

**Configurazione installata (a).**
- Il setup scrive `--spec 4` (iq_kernels.cu L1860; docs/terminal-previews/launch-step7-advanced.txt L17). Per generate.cpp L651-652 `--spec` è la finestra di verify: l'ultimo token accettato più spec−1 draft.
- generate.cpp L3208-3211: con suffix_draft attivo e mtp_max_t=0 si ha mtp_max_t=4 e spec=min(4+2,8)=6. Questo conferma quanto riportato da Scout.
- L11173-11174: S_mtp=min(4,6)=4 e `mtp.set_max_drafts(S_mtp−1)`, quindi l'MTP fa **3 draft**.
- L14897: `sfx.propose(S−1)`, quindi il lookup propone al massimo **5 token**.
- **Scelta: MTP Dmax=3.**

**Verifiche.**
- (b) riproduce esattamente "two"/"two8" dei report precedenti in tutti e 6 gli insiemi: sono uguali al bit.
- min(acc16,7) coincide con lk_acc delle tracce: 0 discrepanze.

## 1. AL per dominio e split

| insieme | n | AL (a) installata | AL (b) T≤8 | AL (c) lookup16 | AL (d) lookup12 |
|---|---|---|---|---|---|
| tune code | 10 | 5,025 | 6,709 | 9,847 | 8,660 |
| holdout code | 30 | 5,073 | 6,831 | 10,397 | 9,051 |
| tune chat | 10 | 2,585 | 2,893 | 2,906 | 2,899 |
| holdout chat | 30 | 2,782 | 3,290 | 3,290 | 3,290 |
| tune edit | 10 | 4,689 | 5,981 | 8,205 | 7,485 |
| holdout edit | 30 | 4,848 | 6,436 | 8,998 | 7,983 |

**ΔAL contro (a), configurazione installata, con [IC95]**

| insieme | (b) T≤8 | (c) lookup16 | (d) lookup12 |
|---|---|---|---|
| tune code | +33,5% [+29,2;+37,8] | +96,0% [+81,3;+114,9] | +72,3% [+63,7;+83,3] |
| holdout code | +34,7% [+32,0;+37,6] | +105,0% [+89,5;+121,3] | +78,4% [+69,3;+87,4] |
| tune chat | +11,9% [+5,9;+21,1] | +12,4% [+6,3;+21,8] | +12,2% [+6,2;+21,2] |
| holdout chat | +18,3% [+13,6;+24,1] | +18,3% [+13,6;+24,1] | +18,3% [+13,6;+24,1] |
| tune edit | +27,6% [+22,4;+34,1] | +75,0% [+47,0;+126,7] | +59,6% [+39,0;+93,6] |
| holdout edit | +32,8% [+28,6;+37,0] | +85,6% [+66,4;+108,9] | +64,7% [+52,4;+78,6] |

**ΔAL contro (b), T≤8 attuale, con [IC95]**

| insieme | (c) lookup16 | (d) lookup12 | quota del guadagno di (c) catturata da (d) = (d−b)/(c−b) [IC95] |
|---|---|---|---|
| tune code | +46,8% [+35,4;+60,0] | +29,1% [+22,7;+35,5] | 62,2% [57,0;67,6] |
| holdout code | +52,2% [+42,2;+63,1] | +32,5% [+27,3;+38,2] | 62,3% [57,1;67,4] |
| tune chat | +0,5% [+0,0;+1,1] | +0,2% [+0,0;+0,7] | 49,9% [0,0;100,0] |
| holdout chat | +0,0% [+0,0;+0,0] | +0,0% [+0,0;+0,0] | n.d. (c=b) |
| tune edit | +37,2% [+19,6;+69,6] | +25,1% [+13,2;+44,6] | 67,6% [62,4;72,7] |
| holdout edit | +39,8% [+27,9;+54,8] | +24,0% [+17,2;+32,0] | 60,4% [53,6;66,6] |

## 2. Lunghezze accettate dal lookup a 16 sopra 7

Ci sono due modi di guardarle:
- **Posizioni.** Quota di tutte le posizioni teacher-forced in cui acc16, troncato a n−i−1, cade in 8–12 o in 13–16.
- **Round.** Nel cammino oracolo (c), quota dei round e dei token per lunghezza accettata a.

La quota del guadagno di AL tra (b) e (c) è data dai tappi:
- 8–12 = (d−b)/(c−b): sono i token dall'8° al 12° di ogni corsa accettata;
- 13–16 = (c−d)/(c−b).

| insieme | posizioni 8–12 | posizioni 13–16 (di cui =16) | round (c) 8–12 / 13–16 | token (c) 8–12 / 13–16 | guadagno 8–12 | guadagno 13–16 |
|---|---|---|---|---|---|---|
| tune code | 5,2% | 63,2% (60,5%) | 5,6% / 40,3% | 5,7% / 69,4% | 62,2% | 37,8% |
| holdout code | 4,4% | 67,0% (64,8%) | 2,0% / 44,9% | 2,1% / 72,5% | 62,3% | 37,7% |
| tune chat | 0,7% | 0,7% (0,2%) | 0,2% / 0,2% | 0,9% / 1,4% | 49,9% | 50,1% |
| holdout chat | 0,1% | 0,0% (0,0%) | 0,0% / 0,0% | 0,0% / 0,0% | n.d. | n.d. |
| tune edit | 5,2% | 59,1% (56,3%) | 0,6% / 32,1% | 1,0% / 66,0% | 67,6% | 32,4% |
| holdout edit | 5,7% | 59,5% (56,6%) | 1,9% / 35,5% | 2,3% / 66,7% | 60,4% | 39,6% |

Nei round di (c) con a ≥ 8 la fonte vincente è sempre il lookup (l'MTP è limitato a 7).

**Istogramma: posizioni per lunghezza accettata dal lookup a 16, 8..16** (troncato a n−i−1; un # vale circa 1% delle posizioni dell'insieme)
```
tune code (posizioni 1221)
   8 | #                                                                    13
   9 | #                                                                    13
  10 | #                                                                    13
  11 | #                                                                    13
  12 | #                                                                    11
  13 | #                                                                    12
  14 | #                                                                    10
  15 | #                                                                    11
  16 | #############################################################        739
holdout code (posizioni 3566)
   8 | #                                                                    33
   9 | #                                                                    33
  10 | #                                                                    31
  11 | #                                                                    31
  12 | #                                                                    28
  13 | #                                                                    28
  14 | #                                                                    26
  15 | #                                                                    27
  16 | #################################################################    2309
tune chat (posizioni 1238)
   8 |                                                                      2
   9 |                                                                      2
  10 |                                                                      1
  11 |                                                                      2
  12 |                                                                      2
  13 |                                                                      2
  14 |                                                                      2
  15 |                                                                      2
  16 |                                                                      3
holdout chat (posizioni 3639)
   8 |                                                                      3
   9 |                                                                      0
  10 |                                                                      0
  11 |                                                                      0
  12 |                                                                      0
  13 |                                                                      0
  14 |                                                                      0
  15 |                                                                      0
  16 |                                                                      0
tune edit (posizioni 1280)
   8 | #                                                                    14
   9 | #                                                                    14
  10 | #                                                                    13
  11 | #                                                                    13
  12 | #                                                                    13
  13 | #                                                                    12
  14 | #                                                                    12
  15 | #                                                                    12
  16 | ########################################################             721
holdout edit (posizioni 3752)
   8 | #                                                                    48
   9 | #                                                                    45
  10 | #                                                                    39
  11 | #                                                                    43
  12 | #                                                                    38
  13 | #                                                                    39
  14 | #                                                                    35
  15 | #                                                                    34
  16 | #########################################################            2123
```

**Lookup12 cattura gran parte del guadagno di lookup16? Sì, circa due terzi, ma non tutto.**
- In code ed edit (d) porta il 60–68% del guadagno di AL tra (b) e (c). I limiti inferiori dell'IC95 sono tra 53,6% e 62,4%.
- Il resto, 32–40%, viene dai token dal 13° al 16°.
- Il motivo: le corse accettate sono quasi tutte **saturate a 16**. In code ed edit il 56–65% delle posizioni ha acc16=16, cioè il tappo della finestra (13–16 nel complesso: 59–67%), mentre 8–12 vale solo il 4–6% delle posizioni.
- La saturazione dice che molte corse copiate sono più lunghe di 16. Questo report non misura finestre più lunghe di 16.
- In chat il guadagno è circa 0: le posizioni 8–16 sono al massimo l'1,4%.

## 3. Regola del Lead (aggiornata)
"ΔAL sotto il 3%: il filone si chiude; tra il 3% e il 10%: 'ipotesi GPU a bassa priorità'; sopra il 10% in code o in edit: ipotesi per il giro GPU, da misurare con s(T) reale."

**ESITO: sopra il 10% in code e in edit**, in tune e in holdout. Quindi è un'**ipotesi per il giro GPU, da misurare con s(T) reale**.
- (c) contro (b): da +37,2% a +52,2%. (d) contro (b): da +24,0% a +32,5%. Il limite inferiore dell'IC95 è ≥ +13,2% in tutti i casi.
- Contro l'installata (a): (c) da +75% a +105%, (d) da +60% a +78%.
- Chat: (c) e (d) contro (b) sono sotto il 3%.
- **Osservazione: la regola non la prevede, la riporto senza decidere.**
  - (b) contro (a) vale +27,6…+34,7% in code ed edit e +11,9…+18,3% in chat.
  - È la parte di tetto già raggiungibile dentro i limiti attuali del motore (T≤8), senza toccare i kernel.
  - Anche questa va misurata con s(T) reale.
  - apps/host/src/lib/tune-values.ts L16 cita "--spec 6 (was 4)" come esito del tuning.

## Limiti
- È un tetto oracolo: miglior fonte a posteriori per round. L'oracolo ignora il gate di produzione `sbuf[0] == drafts[0]` (L14899) e la DraftPolicy. Non è un AL ottenibile da una policy reale e non dice nulla sui tok/s.
- Le uscite sono al massimo 128 token (`-n 128`), quindi le corse lunghe sono tagliate dalla fine della risposta.
- Accettazioni e riferimento greedy vengono dal proxy 2B (llama.cpp, "proxy CPU, non AMD").
- In code ed edit c'è molta copia dal prompt: è proprio lì che il lookup lungo guadagna.
- Oggi il motore ha kVerifyMaxT=8 e DraftPolicy::kMaxT=8. (c) e (d) richiedono di modificare i kernel di verify e la policy.
- Non ho calcolato la regola min(match,16) proposta da Specu (non autorizzata). Sorgenti terze non incluse (filone chiuso).
