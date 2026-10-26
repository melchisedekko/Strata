# check_v12 confermativo v2: STRATA_SPEC_COST=1 contro il default installato (min_p 0,5)

## VERDETTO: NEUTRO
La prima condizione della regola non è soddisfatta: ci sono celle W in code (4) e in edit (3). La seconda invece lo è: chat ha l'IC95 della cella mediana sopra 0.
Come prevede la regola, l'A/B su AMD si fa comunque.

## Riferimenti
- File di run v2 (scritto alle 06:51:51 CET, prima di aprire le tracce, in sola lettura): replay/run_check_v12_v2.json, sha256 68ede3369e22b17b046eb81edef57ab908c030d064cede4b14c635e13173d76c.
- Sostituisce run_check_v12.json (cc5e8cd2…), che si era fermato con rc=3 sul gate di schema.
- Wrapper v2: replay/run_check_v12_wrapper_v2.py, sha256 70aa3a8a…. Il wrapper v1 (c1d47afa…) non è stato toccato.
- Script congelato 6809946d…, non modificato.
- Traccia check_v12_tf_d7.jsonl, sha256 0fe48996… (corrisponde al manifest): 20 richieste per dominio, cluster = richiesta.
- Gate superato:
  - unica differenza di schema rispetto a v1.1: la chiave request `spec_params`;
  - spec_params identici in tutte le 60 richieste: draft_p_min 0.0, n_max 7, n_min 0;
  - manifest, marker e riga TF di cmds.txt coerenti.

## Regola del Lead (testo letterale)
"STRATA_SPEC_COST=1 è raccomandabile contro il default installato solo se ci sono 0 celle W in tutti e tre i domini e almeno un dominio ha l'IC95 della cella mediana sopra 0; se manca una delle due condizioni il verdetto è neutro. In entrambi i casi l'A/B su AMD si fa comunque; il verdetto decide solo quale configurazione proponiamo come default per quella prova."

## Tabella: costo V1, banda di 15 celle (P1/P2/P4 × ρ 0,059–0,1394)
Δ = tok/s STIMATO di SPEC_COST / default installato − 1.

| dominio | cella mediana | Δ mediana [IC95] | [min;max] della banda | W | B |
|---|---|---|---|---|---|
| code | P4 ρ0,1193 | −0,06% [−0,64;+0,54] | [−1,28;+4,48] | 4 (P2 ρ0,059/0,0791/0,1193/0,1394) | 4 |
| chat | P1 ρ0,1394 | +2,77% [+1,39;+4,04] | [+2,49;+3,15] | 0 | 15 |
| edit | P1 ρ0,0791 | +0,67% [−0,02;+1,50] | [−1,85;+1,76] | 3 (P4 ρ0,059/0,0791/0,0992) | 5 |

Il costo V2 è riportato come sensibilità: dà numeri identici a V1 alla seconda cifra decimale.

## Controlli
Griglia P4 cost_T_d (V1):

| dominio | Δ [IC95] | classe |
|---|---|---|
| code | −0,28% [−0,91;+0,30] | neutra |
| chat | +3,19% [+2,24;+3,95] | migliore |
| edit | +0,32% [−0,25;+0,97] | neutra |

ρ = 0,26:

| dominio | P1 | P2 | P4 |
|---|---|---|---|
| code | +0,36% [−0,91;+1,89] | +0,01% [−0,60;+0,62] | −0,46% [−1,16;+0,17] |
| chat | +2,89% [+1,59;+4,09] | +3,93% [+2,89;+4,81] | +3,03% [+2,02;+3,86] |
| edit | +4,03% [+2,21;+5,96] | +0,12% [−0,56;+0,84] | +0,30% [−0,28;+0,95] |

## Limiti
- **Divergenza live/replay su code (dato di Bench).** L'AL della richiesta intera live rispetto al replay è +3,5% per il lookup e +2,8% per combo. Lo scarto dipende dalla divergenza delle traiettorie: sul prefisso comune è al massimo dello 0,3%. Non blocca il confronto.
- I tok/s sono stimati. Le mtp_p vengono dal proxy llama.cpp qwen35-2b ("proxy CPU, non AMD").
- Il JSON dello script congelato riporta in holdout_files_sha256 gli sha dei file v1.1 scritti nel codice. Non sono i dati usati: i dati usati sono check_v12_tf_d7.jsonl.
