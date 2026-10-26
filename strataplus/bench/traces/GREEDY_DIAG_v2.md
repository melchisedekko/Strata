# GREEDY_DIAG v2 — aggiunte del 26/10/2026 (proxy CPU, non AMD)
La v1 (traces/GREEDY_DIAG.md, sha256 0dade97e834ce39492e21b9848d1cdd6cd815540657020bca1e1fe4ead50adc6) resta valida, salvo i punti corretti qui.

## Correzione: tracer da E4 in poi
- La v1 dice "Da E4 in poi: tracer v13". **Non è così:** v13 (proxy/llama_spec_trace_v13.cpp, sha256 2a0a8b7f…) non è mai stato compilato né eseguito.
- E4 e le run successive usano **llama_spec_trace_v14**:
  - sorgente proxy/llama_spec_trace_v14.cpp, sha256 ddea7320ba99054810275d0228c89d1d0b93abd7ab0e1e5584507e739b048283;
  - binario proxy/llama_spec_trace.v14.nollamafile, sha256 e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e;
  - build 26/10 19:33 CET, librerie build-nollamafile con GGML_LLAMAFILE=OFF.
- v14 contiene il clamp EOG di v13: committed = primo EOG incluso, accepted = min(accepted, committed). Registra anche committed_raw ed eos_clamped.
- proxy/llama_spec_trace_v12.cpp (911d6a29…) non è toccato.
- Motivo del cambio di build: la catena precedente (run_agent_v12_post_e4_v3.sh) avrebbe eseguito E4 con v13 su build/ (LLAMAFILE ON). È stata fermata il 26/10 alle 19:28 CET (NOTE in campaign.log) e sostituita da run_agent_v12_post_e4_v4.sh + run_e4_v14.sh.

## agent_v12
- Stesso binario v12 per i 4 modi (tf_d7, live_mtp_k3, live_lookup, live_combo). Il clamp EOS si applica in post-processing (tools/clamp_eos_agent_v12.py).
- I tempi sono **non usabili**:
  - sovrapposizione con cpu_busy_policy.log;
  - box congelato dal 25/10 09:02:32 al 26/10 19:04:47 CET;
  - carico gitleaks di circa 7 core dalle 19:19 alle 19:21 CET;
  - build v14 dalle 19:33:44 alle 19:33:48 CET.
- Le note sono in cpu_busy_bench.log.

## Indipendenza dal cap del draft MTP (nuovo, traces/mtp_cap_prefix_check.json, sha256 349866f270653c9fdced2e8a13a6b9fe94f1f0136aeb015b8c30640acb002ef2)
- Si confrontano cand.mtp.tokens[:min] nelle posizioni con contesto identico (stessi prompt_ids e stesso prefisso di output). Script: tools/mtp_cap_prefix_check.py (sha256 42dd8621…).
- Risultati:
  - live k3 vs k7: 351/378;
  - k1 vs k7: 373/378;
  - k2 vs k7: 284/298;
  - k5 vs k7: 269/306;
  - live k3 p30 (v1.1) vs TF d7: 779/799;
  - agent_turns live k3 vs TF: 878/897;
  - mtbench2: 311/348;
  - **ripetizioni allo stesso cap: 1181/1181**.
- Lettura: il draft MTP di llama.cpp è deterministico a parità di cap e di storia, ma **dipende dal cap e dalla forma dei batch passati, non solo dal contesto**.
  - I primi token divergono già all'indice 0 in alcuni casi.
  - Con draft p_min = 0.0 (common.h L333) non c'è troncamento per probabilità.
- Conseguenza per il replay TF: **la condizione al 100% non è soddisfatta.** Il run file (a′) rigenera un TF a cap 3 e misura la validità (runs/live_combo_aprime_holdout.md §6).

## holdout_lookup_v12, ERRATA 2
- `mtp_process_ms > 0` senza contesto MTP è il residuo del cronometro attorno a un `if (spec && …)` con spec == nullptr.
- Il campo non è valido. Per la regola del Lead, anche i tempi di quei trace non sono validi.
- Dettagli in traces/holdout_lookup_v12_ERRATA_2.md (sha256 9ea774ba7604757e3edb90eebfd573fec28f244c3d14c1f55c4e197145f6f6e1). Corretto in v14 (null).
