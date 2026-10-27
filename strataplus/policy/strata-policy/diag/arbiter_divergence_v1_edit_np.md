# arbiter_divergence_v1 — aggregati edit_np (solo aggregati; dati per prompt solo in /workspace/policy-local/arbiter_diag/)
**Proxy CPU, non AMD, llama.cpp non Strata.** Strata Policy, 2026-10-27 CET. Stessi metodi, PREREG e τ del report code/chat (τ = 0.566763, p99 0.444130).

## T1 (tracce edit_np)
A1: 907/907 round con decisione identica (100%), 0 violazioni. B1: 972/972 (100%), 0 violazioni. 0 valori min_p entro 1e-5 dalla soglia.

## T2 (7/30 prompt divergenti)
- Verdetto per la lettera del PREREG (forme i–iii): FP 1, BUG 2, indeterminato 4 di 7.
- Con le forme non preregistrate (iv)/(v) (storia esatta): FP 7/7, BUG 0.
- Margine top1-top2 in d, forma (i): min 0.0473, max 0.3627 (tutti < τ; nessuno > 10·τ). d: min 9, max 101.
- Top-1 = token A1 / token B1 per forma: (i) 4/3, (ii) 4/3, (iii) 4/3, (iv) 7/0, (v) 0/7.
- (iv)/(v) vs vmargin loggati: 1070 righe, 0 top-1 diversi, |Δgap| max 5e-06.
- I 2 BUG per la lettera sono prompt dove il token di A1 non è top-1 in (i), (ii), (iii) ma lo è nella storia esatta (iv). Dei 4 indeterminati, 3 hanno il token di A1 top-1
  in (i), (ii) e (iii) e quello di B1 top-1 solo nella storia esatta di B1 (v); 1 ha il token di A1 top-1 in (i) e (iv) ma non in (ii), e quello di B1 top-1 in (ii), (iii), (v).

## Comandi
`make_jobs.py div <A1 edit_np>.jsonl <B1 edit_np>.jsonl jobs_div_<suffisso>.txt`; probe con gli stessi flag (-t 6, nice 10); `t2_analyze.py div ... 0.5667629999999981 ... <TF edit_np>.jsonl`.
Job 14:54:58–14:56:29 CET.
