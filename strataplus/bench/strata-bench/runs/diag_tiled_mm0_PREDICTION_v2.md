# diag_tiled_mm0 — previsione v2 (proxy CPU, non AMD, llama.cpp non Strata)

Scritta e hashata: 2026-10-27 15:13:16 CET.
ATTENZIONE: hashata DOPO l'avvio della run aprime_tm0 (15:12:38 CET, env_info_tm0) e PRIMA che chiunque leggesse gli output della prova.
La previsione v1 (diag_tiled_mm0_PREDICTION.md, sha256 2a882b80bb6fe49ae8051bf67b224f0ba78ab2e582c84b08a0017a670aa41df9, 15:11:37 CET) resta valida e invariata.

Testo di Lead (15:12 CET, proposta di Policy):
- con GGML_CPU_TILED_MM=0 spariscono le 18 divergenze A1 vs B1 che iniziano su un round T=8;
- mtbench-105 (pos. 75) e mtbench-136 (pos. 24), T=1 contro T=4, si riportano a parte e non contano né a favore né contro;
- GGML_CPU_TILED_MM_FORCE non impostata; nel log l'ambiente effettivo del processo;
- si riporta quanti dei 60 prompt di A1 coincidono con il greedy puro con il kernel tiled spento.
Se resta anche una sola delle 18 divergenze, la causa non è dimostrata.
