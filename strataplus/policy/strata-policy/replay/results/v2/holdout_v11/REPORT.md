# Holdout v1.1 — report

## 12. Holdout v1.1 (25/10/2026, un solo passaggio, parametri congelati)

**run_holdout_v11.json sha256 5f943d238870f797e792adedf32ecb447e6747696c8601df18a565435dbbe839** (creato 04:26 CET, sola lettura). Aperto alle **04:26:21 CET** (addendum replay/run_holdout_v11_opened.json, sola lettura). Risultati: replay/results/v2/holdout_v11/holdout_v11.json (sha256 752743795627807a6002308e00d951706efb3d82a2546c4812facdb2ee388d1b).

**Dichiarazioni.** I tok/s sono STIMATI dal replay su proxy CPU (Qwen3.5-2B Q4_K_M), non sono misure AMD. Valgono solo per la sequenza singola. Il tune aveva 10 prompt per dominio, l'holdout 30 (90 richieste, 10.957 round, 0 target_mismatch, 1 richiesta per sessione → bootstrap a cluster = per richiesta).

**Gate (tutti passati prima dell'apertura).** (a) file di run 444 con manifest 34bdc195… e frozen 37bf1996…; (b) `sha256sum -c MANIFEST.sha256` (da traces/v1.1) 24/24 OK, frozen 37bf1996…, P4 e51712c6… invariato; (c) k_cap non è letto da nessun .py: postprocess.load_tf ricalcola il lookup con NativeSuffixDrafter.scan(y, DMAX=7); (d) dry run del parser su tf_d7_p30.jsonl (tune v1.1): 30 richieste, 10/dominio, 3.739 round, 0 scarti, 0 mismatch, gen_index==pos, ref_tokens==request_end.output_ids. Campi nuovi ignorati senza effetto: k_cap, config_label, split, acc_ref, lookup_max_match, cand.mtp.probs_sampler; cand.mtp.ent ora presente ma usato solo con conf_stop (spento in A/B/H).

**Verdetto: vince A.** B fallisce la regola in entrambe le versioni del costo: rispetta "batte A su code/edit" (30/30 celle di fascia code+edit con IC95>0, V1 e V2), ma ha 2 celle nettamente peggiori di STRATA_SPEC_COST=1 (identiche in V1 e V2):
- chat|P1|ρ0,059: −2,0% [−3,6; −0,6]
- chat|P1|ρ0,1193: −1,0% [−2,3; −0,0] (limite superiore ≈0, borderline)
Nessuna cella peggiore contro default o k=3, nessuna nel controllo 0,26.

**Celle nettamente peggiori (V1 = V2).**
- A: 1 vs spec_cost, chat|P1|ρ0,0791 −1,4% [−2,8; −0,2]; 0 vs default, 0 vs k=3, 0 nel controllo. *Anche A quindi non soddisfa il criterio "nessuna cella peggiore"; la regola assegna comunque A come esito di default.*
- B: 2 vs spec_cost (sopra); 0 vs default e k=3.
- B vs A: 1 cella peggiore, chat|P1|ρ0,059 −0,8% [−1,5; −0,1]. Fascia: V1 33 meglio/11 neutre/1 peggio; V2 31/13/1.
- H (esplorativo): 4 vs spec_cost (chat|P1 ρ0,059–0,1193, da −1,8% a −2,2%); vs A 0 peggiori; vs B 2 (V1)/1 (V2) peggiori, nessuna in chat.

**Guadagni in fascia (punto [IC95], V1; V2 uguale per A, B leggermente più basso).**
- code: A vs default da +3,4% [+2,2; +4,7] a +10,8% [+9,3; +12,4]; B vs default da +6,3% [+5,4; +7,2] a +25,3% [+22,1; +28,7] (V2 +22,6% [+20,0; +25,4]); B vs A da +2,3% a +14,2% (V2 +10,7%), 15/15 meglio.
- edit: A vs default da +3,0% [+1,3; +5,1] a +10,4% [+8,4; +12,8]; B vs default da +6,8% [+5,0; +8,9] a +21,8% [+17,0; +27,0] (V2 +19,2% [+15,0; +23,7]); B vs A da +1,9% a +12,8% (V2 +9,7%), 15/15 meglio.
- chat: A vs default da +9,0% [+6,3; +11,9] a +24,3% [+19,0; +29,9]; B praticamente uguale (+10,6…+24,2%); vs spec_cost entrambi ≈0 (A −1,4…+2,5%, B −2,0…+3,0%).
- Quota di round di B a T=8: 24,3% (V1), 23,6% (V2); nessun round a T≥9.

**Confronto col tune (tf_d7, 10/dominio).** Nel tune A e B avevano 0 celle peggiori contro le baseline in V1 e V2; nell'holdout compaiono 1 (A) e 2 (B) celle chat lievemente peggiori di spec_cost, tutte P1, effetti di 1–2%. La dominanza di B su A in code/edit si conferma e si rafforza (tune 21 celle code/edit meglio, holdout 30/30); quota T=8 sale da 18,65%/17,80% a 24,3%/23,6%. Il file tune v1.1 (tf_d7_p30) non coincide con tf_d7 usato per il tune: lo stesso script su di esso dà A 3 e B 2 celle chat peggiori di spec_cost (P2/P4, −1,4…−1,9%) — il segnale chat vs spec_cost era già presente sui dati v1.1 ma con celle diverse, quindi è rumore di bordo vicino a 0 più che un effetto stabile.

**Anomalie / bug.** Nessun bug trovato nel run, nulla è stato rifatto. Note per il Lead: (1) A vince per default ma viola anch'esso il criterio "0 celle peggiori" (1 cella chat vs spec_cost); (2) una delle due celle che fanno fallire B ha limite superiore ≈0 (−0,0); (3) le celle peggiori migrano tra P1 (holdout) e P2/P4 (tune v1.1), segno di instabilità su chat vs spec_cost. La decisione spetta al Lead.
