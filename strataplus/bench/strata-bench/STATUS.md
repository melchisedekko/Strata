# STATUS Strata Bench — aggiornato 2026-10-26 20:14:44 (CET)
Etichetta: proxy CPU, non AMD. Nessun push, nessuna PR.

## Processi in corso (non uccidere)
- run_agent_v12.sh, PID 376117. È il padre di live_mtp_k3 (PID 437326, llama_spec_trace.v12.nollamafile).
  - live_mtp_k3 COMPLETATO 23/23 (.ok, exit 0, g9_violations=0), finestra CPU chiusa 20:14:05; segue lookup/combo (automatico).
  - Poi lancia live_lookup e live_combo con gli stessi flag, e alla fine scrive traces/raw/agent_v12/runs.done.
- run_agent_v12_post_e4_v4.sh, PID 481441 (log logs/run_agent_v12_post_e4_v4.out). Attende runs.done, poi:
  1. annotate;
  2. post;
  3. clamp EOS;
  4. timing flag "non usabili";
  5. validate;
  6. divergence;
  7. MANIFEST e AGENT_V12_READY in traces/agent_v12/;
  8. E4 con run_e4_v14.sh (tracer v14, LLAMAFILE OFF), tag e4v14_tf_d7_p30_{full,dvocab,dvocab_en}, poi e4v14.done.
- La catena v3 (E4 con v13 su build/ LLAMAFILE ON) è stata fermata prima di partire (NOTE in campaign.log).

## Fatto (file nuovi, read-only, con .sha256 accanto)
| file | sha256 |
|---|---|
| proxy/strata_arbiter_v1.hpp | 85bb5341d9995d495bd2dd72ba52349ccccbed4497eeb00da67e1b500d8e7c19 |
| proxy/strata_arbiter_v1.py | 2b0e8b9a0c45d6927dca09db8f352a288305f5521e0c874ff45d4c87bf46611a |
| proxy/llama_spec_trace_v14.cpp | ddea7320ba99054810275d0228c89d1d0b93abd7ab0e1e5584507e739b048283 |
| proxy/llama_spec_trace.v14.nollamafile | e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e (compilato, **mai eseguito**) |
| tools/mtp_cap_prefix_check.py | 42dd8621503ef07dbea6e34d1ca22791e001fed95062d7970898a81b6fc8b993 |
| tools/aprime_post.py | 808ebcc95997fef256bb4f3642f5740ff2aa6c4755a3c34750c20eecaab82e3e |
| runs/run_live_combo_aprime_holdout.sh | 5066b06a… (SUPERATO dalla v2, mai lanciato) |
| runs/live_combo_aprime_holdout.md | 8df75e27… (SUPERATO dalla v2; contiene gli ID di edit_np) |
| runs/run_live_combo_aprime_holdout_v2.sh | e1140052619d4dd9c672c96f0926f0399c113f21382595d6e7f2813067c51ace (**non lanciato**) |
| runs/live_combo_aprime_holdout_v2.md | 3d734b32f979b4cd952547d0ae8cf9f1b4cdf29e91b9b7b154bc0ed3cbba0e04 |
| datasets/holdout_90_codechat.jsonl / holdout_90_edit_np.jsonl | 18288525… / 6b2404c8… |
| datasets/proxy_30_codechat.jsonl / proxy_30_edit_np.jsonl | 89c28ff8… / 221ce769… |
| strata-plus/traces/AMD_PROTOCOL_v3.md | e963d80a02d19cd276ad19f0d1a50dbb629d1b4878baf9fcc48346d87d8ce59f (sostituisce la v2) |
| strata-plus/traces/mtp_cap_prefix_check.json | 349866f270653c9fdced2e8a13a6b9fe94f1f0136aeb015b8c30640acb002ef2 (5210/5389, non al 100%) |
| strata-plus/traces/holdout_lookup_v12_ERRATA_2.md | 9ea774ba7604757e3edb90eebfd573fec28f244c3d14c1f55c4e197145f6f6e1 |
| strata-plus/traces/AMD_PROTOCOL_v2.md | cb52924b78778d32b3f2d46c879d7b8a5df6a1adddedce4e83c631756cbcc842 |
| strata-plus/traces/GREEDY_DIAG_v2.md | c5e51b10b7e13de6f8308513cf409a48db84bca34956e63bf5be4d880bf22282 |
| strata-plus/traces/LOG_SCHEMA_v2.md | 7ddba21278636e028f1a9cd49701453cc9f6446f770845d11a9332f1cb1816a4 |
| strata-plus/traces/SUMMARY_v2.md | c310626f4ab235cf7fa1157d2828e88d4eba3d0d2866902e68855f97feb040c5 |

## Regola sul dataset di edit con licenza non pubblicabile, `edit_np` (Alessandro, 19:45 CET)
- Gli artefatti nuovi del dominio edit hanno nel nome un'etichetta locale del dataset (in questo documento scritta `edit_np`). Vale per la run (a′) v2 e per E4: run_e4_v14.sh è stato modificato prima di partire, nuovo sha 8da5f5f7…, copia in logs/run_e4_v14.pre_edit_np.sh.bak. I tag edit sono e4v14_tf_d7_p30_<n>_edit_np.
- I report contengono solo aggregati per dominio.
- Inventario dei file esistenti con ID edit per richiesta: logs/edit_per_request_inventory_20261026.txt (271 file).

## HumanEvalFix (GO di Lead)
- datasets/humanevalfix_9a41762f/: cartella nuova, licenza MIT. Contiene i 5 parquet non Python, README, LICENSE_NOTE.md e SHA256SUMS (sha256 3341a36c…).
- Nessuna traccia generata.
- LANG_COUNT_editfix.json 9ea608a8… / .md ba6a4190… (tools/lang_count_editfix.py 3a75dd86…): 164 item × 5 linguaggi, N 0–163 tutti presenti nei 5.
- pyarrow in venv /tmp/venv_pa (fuori da /workspace).

## In coda
- Inventario H-LANG: dopo la fine di agent_v12 (runs.done e post-processing).
- Nessun run file per edit-fix: si aspetta lo split di Policy.

## Cartelle nuove (sync pubblico)
- /workspace/strata-bench/runs/: contiene solo script e md. Niente segreti, niente dati con licenza non permissiva.
- /workspace/strata-plus/traces/raw/aprime_holdout_v14/: verrà creata solo quando la run (a′) sarà lanciata. Il dataset è MIT/Apache-2.0.

## Non fatto
- Smoke test del tracer v14: arriva solo con E4.
- Run (a′): non lanciata, come da istruzioni.
- Nessun numero AL di agent_v12 o E4 riportato finché le catene non finiscono.
- README_v2 non scritto: SUMMARY_v2 copre lo stato. Lo stato vecchio resta in README/SUMMARY v1, che sono intatti.
- Nessun numero AMD.

## Log CPU
- /workspace/strata-bench/cpu_busy_bench.log è un symlink a /workspace/strata-plus/cpu_busy_bench.log, scritto da bench_window_log.py (PID 321436).
- Ogni run scrive anche il suo cpu_*.log.
