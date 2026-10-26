# Oracolo a finestra lunga (lookup, Suffix e ngram_mod fino a 16): solo AL, descrittivo, indipendente dall'hardware

**Cos'è.** Un limite superiore offline dell'AL. Non dà tok/s e non dice nulla sul costo.
- MTP resta a Dmax=7, con le accettazioni prese dalle tracce v1.1 (proxy llama.cpp 2B, "proxy CPU, non AMD").
- Lookup, SuffixDecoding e common_ngram_mod propongono fino a 16 token; la finestra non-MTP è quindi 16+1.
- Accettazione = lcp(cand[:16], y[p:p+16]), dove y è il riferimento greedy completo della richiesta.
- Il lookup è **rigenerato**, non letto dalle tracce, con il SuffixDrafter di produzione (sd_scan nativo, min_match 3, max_match 64, max_k 16).
- Oracolo per round: a = max tra le sorgenti, troncato a n−i−1. AL = N/round, senza memoria tra una richiesta e l'altra.
- Bootstrap B=2000, seed 0, sulle richieste.
- La logica è ripresa da ceiling_third_source.py (550f480a…, non modificato).
- Script: replay/ceiling_long_window.py.

**Contesto (Scout, codice @7dd5cf1).** Oggi kVerifyMaxT=8 e DraftPolicy::kMaxT=8. Una finestra di 16 è quindi **solo un'ipotesi per il round GPU** e richiede di modificare i kernel di verify e la policy.

## Controlli
- **y completo, nessun troncamento dei dati.** In tutte le 120 richieste (tune 30, holdout 90):
  - len(ref_tokens) è uguale a output_tokens registrato;
  - i round coprono tutte le posizioni 0..n−1.
- Le richieste con n<128 si sono fermate prima del limite `-n 128` (EOS). Sono 1/1/0 nel tune e 8/4/3 nell'holdout (code/chat/edit).
- Vicino alla fine di una richiesta l'lcp è limitato in modo naturale da n−i−1. È un limite della risposta, non un troncamento dei dati.
- **Lookup rigenerato contro tracce.** min(acc16, 7) coincide con lk_acc delle tracce (lookup registrato, tagliato a 7) in tutte le posizioni: 0 discrepanze su 14.696.
- La baseline MTP+lookup T≤8 riproduce esattamente "two" di ceiling_third_source in tutti i 6 insiemi.
- **Saturazione a 7.** Il lookup a 16 accetta ≥8 token in molte posizioni:
  - code: 69% tune, 72% holdout;
  - edit: 65% tune, 66% holdout;
  - chat: 1,5% tune, 0,1% holdout.

## Tabella: AL e ΔAL rispetto a MTP+lookup T≤8, con [IC95]

| insieme | n | AL T≤8 | AL lookup16 | Δ lookup16 | AL +Suffix16 | Δ +Suffix16 | AL +ngram_mod16 | Δ +ngram_mod16 |
|---|---|---|---|---|---|---|---|---|
| tune code | 10 | 6,709 | 9,847 | +46,8% [+35,4;+60,0] | 9,927 | +48,0% [+36,2;+61,3] | 9,927 | +48,0% [+36,2;+61,3] |
| holdout code | 30 | 6,831 | 10,397 | +52,2% [+42,2;+63,1] | 10,582 | +54,9% [+44,4;+66,3] | 10,741 | +57,2% [+46,1;+69,6] |
| tune chat | 10 | 2,893 | 2,906 | +0,5% [0,0;+1,1] | 2,906 | +0,5% [0,0;+1,1] | 2,906 | +0,5% [0,0;+1,1] |
| holdout chat | 30 | 3,290 | 3,290 | 0,0% [0,0;0,0] | 3,314 | +0,7% [+0,1;+1,9] | 3,305 | +0,5% [0,0;+1,5] |
| tune edit | 10 | 5,981 | 8,205 | +37,2% [+19,6;+69,6] | 8,258 | +38,1% [+19,8;+71,6] | 8,258 | +38,1% [+19,8;+71,6] |
| holdout edit | 30 | 6,436 | 8,998 | +39,8% [+27,9;+54,8] | 9,151 | +42,2% [+29,5;+58,1] | 9,151 | +42,2% [+29,5;+58,1] |

ngram_mod: n_match 24, n_max 16, n_min=min(48,16)=16. Come sensibilità, con n_min=1 si ottengono valori identici in tutti gli insiemi.

## Scomposizione del guadagno
1. **Finestra lunga del lookup** (lookup16 rispetto a T≤8):
   - code: +46,8% tune, +52,2% holdout;
   - edit: +37,2% tune, +39,8% holdout;
   - chat: circa 0.
2. **Terza sorgente** (incremento rispetto a MTP+lookup16, IC95):

| insieme | +Suffix16 | +ngram_mod16 |
|---|---|---|
| tune code | +0,8% [0,0;+2,7] | +0,8% [0,0;+2,7] |
| holdout code | +1,8% [+0,5;+3,5] | +3,3% [+1,1;+6,0] |
| tune chat | 0,0% | 0,0% |
| holdout chat | +0,7% [+0,1;+1,9] | +0,5% [0,0;+1,5] |
| tune edit | +0,7% [0,0;+2,4] | +0,7% [0,0;+2,4] |
| holdout edit | +1,7% [+0,7;+3,1] | +1,7% [+0,7;+3,1] |

Quasi tutto il guadagno viene dalla finestra lunga del lookup. La terza sorgente aggiunge al massimo circa 3% (ngram_mod sull'holdout code).

## Regola del Lead
"ΔAL <3% ovunque → la linea si chiude; >10% in code o edit → ipotesi per il round GPU, da misurare con s(T) reale; 3–10% → zona non coperta, decide il Lead."

**ESITO: >10% in code e in edit**, sia nel tune sia nell'holdout, con il limite inferiore dell'IC95 ≥ +19,6%. Quindi è **un'ipotesi per il round GPU, da misurare con s(T) reale**. Chat resta sotto il 3%.

## Limiti
- È un oracolo per round: un limite superiore dell'AL, non un AL ottenibile da una policy reale.
- Non dice nulla sui tok/s. Il costo di verify per T fino a 17 non esiste in s(T) oggi: va misurato su GPU dopo aver modificato i kernel (kVerifyMaxT) e la policy (kMaxT).
- Le uscite sono al massimo di 128 token e il riferimento greedy viene dal proxy 2B. In code ed edit c'è molta copia dal prompt.
