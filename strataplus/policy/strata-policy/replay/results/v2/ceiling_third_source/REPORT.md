# Studio del tetto: terza fonte (SuffixDecoding / common_ngram_mod) contro l'oracolo MTP+lookup. Descrittivo, offline, nessun modello
Script: replay/ceiling_third_source.py. Dati: ceiling_third_source.json. Esecuzione: 06:48:19–06:48:25 CET, nice 19, single-thread, rc=0.
Tracce v1.1 di Bench (sha nel JSON):
- tune: tf_d7_p30 (87efe507…), 10 richieste per dominio;
- holdout: holdout_{code,chat,edit}_tf_d7, 30 richieste per dominio;
- agent_edit: agent_turns_bench_tf_d7 (be5854b7…).
Costo: V1, cost_p4_cpu.json.

**Questo è un LIMITE SUPERIORE.** L'oracolo sceglie per ogni round, a posteriori, la fonte che fa accettare più token. Una policy reale ne cattura solo una parte.
- I tok/s sono STIMATI con il costo M-real: draft MTP = max(d,1); lookup e terza fonte pagano ρ_lu·k.
- Le probabilità MTP vengono dal proxy llama.cpp 2B su CPU, non AMD.
- **Non ci sono sessioni agentiche reali.**

## Metodo
- Finestra d≤7 per tutte le fonti. Ogni round produce a+1 token.
- Nessuna memoria fra richieste: tetto per richiesta.
- In caso di parità vince la fonte più economica.
- IC95: bootstrap con B=2000 e seed 0, sulle richieste (per agent_edit sulle sessioni).

Fonti:
- **SuffixDecoding**: riproduzione dall'algoritmo documentato, NON dal sorgente ArcticInference (non c'è un clone locale).
  - Parametri: default vLLM, cioè max_tree_depth 24, max_spec_factor 1,0, min_token_prob 0,1.
  - Indice di suffissi per richiesta su prompt + output generato fino a quel punto.
  - Per ogni lunghezza di match si segue il percorso più frequente; vince il percorso con lo score migliore.
- **common_ngram_mod**: llama.cpp @d327bf1f.
  - ngram-mod.cpp L15-25 (hash), L27-35 (add).
  - speculative.cpp L2106 (tabella da 4M voci), L2124-2150 (begin), L2152-2206 (draft_one: add a blocchi di 32, n_min), L2226-2251 (reset dopo 5 round con accettazione bassa).
  - Default in common.h L360-363: n_match 24, n_max 64, n_min 48. n_max è tagliato a 7; n_min vale 7 nella variante A e 1 nella variante B.

## (a) AL degli oracoli: tokens per round
| split / dominio | MTP+lookup | +Suffix | Δ AL [IC95] | +ngram_mod A (B identico) | Δ AL [IC95] |
|---|---|---|---|---|---|
| tune code | 6,709 | 6,709 | 0,00% [0,00;0,00] | 6,709 | 0,00% |
| tune chat | 2,893 | 2,893 | 0,00% [0,00;0,00] | 2,893 | 0,00% |
| tune edit | 5,981 | 5,981 | 0,00% [0,00;0,00] | 5,981 | 0,00% |
| holdout code | 6,831 | 6,871 | +0,58% [0,00;+1,49] | 6,871 | +0,58% [0,00;+1,49] |
| holdout chat | 3,290 | 3,302 | +0,36% [+0,08;+0,72] | 3,290 | 0,00% |
| holdout edit | 6,436 | 6,469 | +0,52% [0,00;+1,19] | 6,469 | +0,52% [0,00;+1,19] |
| agent_edit per richiesta (tune) | 6,124 | 6,134 | +0,16% [0,00;+0,45] | 6,134 | +0,16% [0,00;+0,45] |
| agent_edit H2a, pool di sessione (tune) | 6,124 | 6,134 | +0,16% [0,00;+0,45] | 6,134 | +0,16% [0,00;+0,45] |

## (b) tok/s stimati, banda di 15 celle (P1/P2/P4 × ρ 0,059–0,1394)
Il valore è la cella mediana per Δ, con [min;max] della banda.
| split / dominio | Δ con Suffix: mediana [IC95] (banda) | Δ con ngram_mod A: mediana [IC95] (banda) |
|---|---|---|
| tune code | +0,51% [−0,00;+1,28] (+0,22…+1,00) | identico a Suffix |
| tune chat | 0,00% | 0,00% |
| tune edit | +0,17% [−0,00;+0,46] (+0,07…+0,34) | +0,14% [−0,00;+0,43] (+0,06…+0,26) |
| holdout code | +0,67% [+0,17;+1,34] (+0,28…+1,22) | +0,65% [+0,15;+1,32] (+0,27…+1,18) |
| holdout chat | +0,34% [+0,04;+0,85] (+0,14…+0,51) | +0,20% [0,00;+0,63] (+0,09…+0,32) |
| holdout edit | +0,53% [+0,21;+0,93] (+0,22…+0,92) | +0,50% [+0,19;+0,88] (+0,20…+0,84) |
| agent_edit (tutte e due le varianti) | +0,36% [+0,14;+0,59] (+0,15…+0,66) | identico a Suffix |

Sul tune il guadagno in tok/s arriva con ΔAL = 0. Viene dai pareggi in cui la terza fonte sostituisce l'MTP con lo stesso numero di token accettati, ma con 1 solo draft da pagare. È un effetto di contabilità, non token in più.

## Soglia del Lead
Serve ≥3% sul tune, confermato sul holdout. **Nessun dominio la supera**, né in AL né in tok/s, né con SuffixDecoding né con ngram_mod. Il valore massimo è +0,58% di AL (holdout code). Sul tune la ΔAL è 0 in tutti i domini.

## Note
- **Il tetto è schiacciato dal limite di finestra 7.** L'oracolo MTP+lookup è già a 6,7–6,8 token per round su code, su un massimo di 8. Sul holdout code il 67% delle posizioni ha mtp_acc = 7.
- Le varianti A e B di ngram_mod coincidono. I match a 24 token arrivano in sequenze lunghe, quindi n_min non conta.
- agent_edit:
  - solo 10 sessioni × 3 turni, costruite dal dataset di edit con licenza non pubblicabile (`edit_np`);
  - solo tune, descrittivo, senza conferma su holdout;
  - non sono le sessioni reali di tools/agent_turns_bench.py;
  - la licenza è ancora in verifica da parte di Bench, quindi i dati sono usati solo per questo calcolo offline.
- Il pool H2a coincide con il caso per richiesta. I prompt dei turni 1 e 2 contengono già i turni precedenti (lunghezze 275 → 2751 → 2923 token), quindi il pool non aggiunge testo nuovo. Nel pool il lookup usa load_tf pl_* con pool_scope=session; ngram_mod usa una tabella condivisa nella sessione, come nel server.
