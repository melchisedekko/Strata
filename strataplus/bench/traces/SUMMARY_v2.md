# SUMMARY v2 — stato al 26/10/2026 (proxy CPU, non AMD)
Le versioni precedenti (SUMMARY.md, README.md) non sono toccate. Questo file aggiunge solo lo stato nuovo. **Nessun numero di tempo è un risultato.**
- **agent_v12:**
  - tf_d7 completato: 23/23 richieste;
  - live_mtp_k3 in corso (PID 437326, figlio di run_agent_v12.sh PID 376117);
  - poi live_lookup e live_combo li lancia run_agent_v12.sh;
  - poi il post-processing e E4 v14 li lancia run_agent_v12_post_e4_v4.sh.
  - Stato aggiornato in /workspace/strata-bench/STATUS.md.
- **Tracer v14** e **arbitro** proxy/strata_arbiter_v1.hpp (+ .py): GREEDY_DIAG_v2.md, LOG_SCHEMA_v2.md.
- **Pre-check del cap MTP:** non al 100% (mtp_cap_prefix_check.json, sha256 349866f270653c9fdced2e8a13a6b9fe94f1f0136aeb015b8c30640acb002ef2).
- **ERRATA 2** su holdout_lookup_v12: holdout_lookup_v12_ERRATA_2.md.
- **Run (a′) vs default (a):** /workspace/strata-bench/runs/live_combo_aprime_holdout.md + script. Scritti e hashati, **non lanciati**.
- **Protocollo AMD v2:** AMD_PROTOCOL_v2.md (gate, binario e441f3a, H-LW, EMA, H-FC). Nessun numero AMD esiste.
