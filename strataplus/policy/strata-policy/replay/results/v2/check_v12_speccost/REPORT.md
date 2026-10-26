# check_v12 confermativo — STRATA_SPEC_COST=1 vs default installato (min_p 0,5) — ESITO: STOP AL GATE DI SCHEMA, NESSUN VERDETTO
File di run (scritto prima di aprire le tracce, non modificato, chmod a-w): replay/run_check_v12.json, sha256 cc5e8cd24a8676d88b5f154b1aaf794a80ef488a21c26fa1ceb7a3cc140f425d.
Manifest 22073b2a… e marker 80f25713… verificati; le 10 voci del manifest corrispondono.

## Cosa è successo
Il wrapper congelato (run_check_v12_wrapper.py, sha256 c1d47afa…) ha letto solo i metadati di check_v12_tf_d7.jsonl e si è fermato (exit 3) PRIMA di eseguire lo script congelato: nessuna metrica letta, nessun replay, nessun numero.
- Differenze di schema rispetto a holdout v1.1: un solo campo AGGIUNTO nei record request, `spec_params`; nessun campo mancante; record round identici (chiavi).
  schema "strataplus.v1.1", data_kind teacher_forced, dmax 7, domini code/chat/edit 20+20+20 richieste.
- Il controllo draft_p_min / n_max / n_min del wrapper cercava le chiavi `draft_p_min`, `n_max`, `n_min` al primo livello del request/round e non le ha trovate:
  i valori sono dentro `spec_params` con nomi diversi. Lettura manuale dei soli metadati (60/60 richieste identiche):
  `draft_p_min: 0.0` (default common/common.h:333), `draft_n_max_cli: 7`, `draft_n_max_impl: 7`, `draft_n_min: 0` (common/common.h:330), `mtp_layers: 1`.
- Per regola ("se lo schema è diverso, fermati e riporta la differenza senza adattare niente") e perché il file di run fissa lo sha256 del wrapper, NON ho corretto il wrapper né riscritto il file di run.

## Serve una decisione del Lead
Per eseguire serve un wrapper v2 il cui gate legga `spec_params.draft_p_min` / `draft_n_max_*` / `draft_n_min` (analisi invariata) e un NUOVO file di run (es. run_check_v12_v2.json) con il suo sha256, registrato prima di leggere metriche. Le metriche di check_v12 non sono ancora state lette.

## Limite da riportare quando il confronto sarà eseguito (Bench)
Su code l'AL della richiesta intera live vs replay è +3,5% (lookup) e +2,8% (combo), dovuto alla divergenza delle traiettorie; sul prefisso comune lo scarto è ≤0,3% secondo Bench. Non bloccante.
