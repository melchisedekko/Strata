# diag_greedy_aprime v1 + diag_tiled_mm0 v1 — divergenza greedy della run (a') v3

**proxy CPU, non AMD, llama.cpp non Strata.** Diagnosi non temporizzata: si misura solo l'identità di output e logit. I tempi di queste finestre **non valgono** (CPU condivisa con build di Policy/Scout e con i probe di Policy).
Dataset edit indicato come `<ET>`: qui solo aggregati (dettaglio in `diag_greedy_aprime_v1/diag_greedy_aprime_v1_edit_np.md`; per prompt solo nel file locale `diag_greedy_aprime_v1/edit_perprompt_<ET>.md`, da non pubblicare).

**Braccio -fa off e tracce edit-fix rinviati per budget (ordine di Alessandro, 15:35 CET).** `runs/diag_fa_off_tm0_PREDICTION.md` (95e6e724…) e `runs/run_diag_fa_off_tm0_v1.sh` (6b63e00f…) sono stati scritti e hashati alle 15:17 CET, ma il braccio **non è stato lanciato**. Anche `runs/run_diag_tiled_mm0_full_v1.sh` (A1 su tutti i 90, ff6db304…) è stato hashato e **non è stato lanciato**.

## Verdetti

- **Bug dell'arbitro, del tracer o della verifica: nessuna evidenza.** Su tutte le prime divergenze misurate (v3 e TILED_MM=0) ogni braccio emette il top-1 dei propri logit: 0 casi di token emesso ≠ top-1 e 0 violazioni del criterio BUG (gap ≥ 0.5). Tutti i gap alla divergenza sono < 0.5 (max 0.38187 code/chat, 0.44916 edit). A1, B1 e greedy sono deterministici bit per bit fra rilanci.
- **Domanda di Lead: cambia anche il baseline con il batch (virgola mobile) o solo con l'arbitro (bug)?** Cambia anche il baseline, per motivi numerici.
  - Il greedy puro batch 1 con GGML_CPU_TILED_MM=0 (base_tm0) differisce dal greedy puro di default (base_r1) su 12/19 prompt code/chat. È una variabile del kernel matmul che l'arbitro non tocca.
  - Con TILED_MM=0 i vmargin cambiano già nel round 0 (logit del prefill) e in tutti i round, anche quelli con T<8.
  - Quindi i logit dipendono dal percorso di kernel / forma del batch, e le divergenze nascono su quasi-pareggi (top-1 e top-2 si scambiano).
- **Previsione v1** (`diag_tiled_mm0_PREDICTION.md`, sha256 2a882b80bb6fe49ae8051bf67b224f0ba78ab2e582c84b08a0017a670aa41df9; è quella che fa fede): **FALLITA.**
  - A1 = B1 su **19/20** prompt divergenti: code/chat 13/13, edit 6/7. Resta 1 divergenza edit.
  - A1 = greedy puro: **non vale**. Sui 20 divergenti, contro il greedy puro già generato (base_r1 = TF3): code/chat 1/13, edit 3/7.
  - Contro il greedy rigenerato con TILED_MM=0 (solo code/chat, dato descrittivo, vedi limiti): 9/13.
  - Il confronto A1 vs greedy su 60/60 e 30/30 con TILED_MM=0 non è stato misurato (run completa annullata per budget). In ogni caso è già < 60/60 perché falliscono i prompt del sottoinsieme.
  - Alla lettera: «Se resta anche una sola divergenza, la causa del percorso tiled non è dimostrata.» → la causa tiled **non è dimostrata**.
- **Previsione v2** (`diag_tiled_mm0_PREDICTION_v2.md`, f26643da…; secondaria, scritta dopo l'avvio di aprime_tm0, prima di leggere gli output): **non confermata.**
  - Delle 18 divergenze del gruppo "T=8" (11 code/chat + 7 edit) ne spariscono **17/18**: code/chat 11/11, edit 6/7. Resta la stessa divergenza edit (pos 69).
  - Alla lettera: «Se resta anche una sola delle 18 divergenze, la causa non è dimostrata.»
  - mtbench-105 e mtbench-136 (a parte, non contano) con TILED_MM=0: A1 = B1 in entrambi.
  - Il punto di v2 «quanti dei 60 prompt di A1 coincidono con il greedy puro con il kernel tiled spento» non è misurato (budget).
- **Nuova divergenza con TILED_MM=0:** mtbench-132, che non è tra i 20 (in v3 aveva A1 = B1). Diverge A1:B1 a pos 64 con T=4 contro T=4, celle 278/279.
  - Gap: A1 0.01236, B1 0.04586. Ciascun braccio emette il proprio top-1.

## Definizioni e riconciliazione con Policy (`policy-local/arbiter_diag/code_review_verify_commit.md` §5)

- **Le mie "posizioni"** sono la prima differenza di **token di output** fra due run. La colonna T è il T del round che contiene quel token.
- **Policy** (§5, riga 71) usa la prima differenza **numerica** (vmargin) fra i bracci, che viene prima.
- **Verificato sulle tracce v3:**
  - mtbench-105 a pos 75: round A1 T=4, round B1 T=1, kv_pos 296 / ctx_len 297. Stesso top-1 1637, gap 2.31834 contro 2.21047, quindi i logit differiscono ma il token no. Il token di output diverge a pos 100.
  - mtbench-136 a pos 24: A1 T=4, B1 T=1, kv_pos 295 / ctx_len 296. Top-1 25039, gap 1.71971 contro 1.776. L'output diverge a pos 30.
  - Le due definizioni sono coerenti.
- **Gruppo "T=8" di Policy:** ho contato quanti round con T=8 A1 ha prima della prima differenza di output.
  - ≥1 su 11/13 code/chat (tutti tranne mtbench-105 e -136) e su 7/7 edit, cioè le 18 di Policy.
  - B1 non ha mai T=8 (S=6).
  - Il round che contiene il token divergente ha T=8 solo in 2/20 casi (HumanEval/148 e 1 edit). La differenza numerica nasce sul round T=8 e si propaga nello stato fino al primo quasi-pareggio.
- **I 13 code/chat divergenti A1/B1** (v3, controllati: corrispondono ai 13/60 di Policy): HumanEval/13, 35, 55, 59, 91, 101, 148, mtbench-101, 105, 115, 121, 129, 136.
- **Gli altri 6 del sottoinsieme da 19:** mtbench-132 (A1 = B1 ma ≠ TF3) e 5 controlli identici (HumanEval/2, 23, 28, mtbench-113, 134).
- **Inversione dei nomi:** nello script v3, A1 = `--live-src aprime` (S=8) e B1 = `--live-src default_a` (S=6). È invertito rispetto a "A=default_a, B=aprime" del primo messaggio. Qui uso i nomi dello script.

## Tabella per prompt (code/chat, i 13 divergenti)

Il greedy puro è G = base_r1 (batch 1, identico a base_r2 e TF3). Gtm0 = base_tm0. "=" significa identico, "@n" la prima differenza di output.

| id | v3 div A1:B1 | T A1/B1 (round del token) | celle A1;B1 (kv_pos/ctx_len) | round T=8 di A1 prima | v3 A1:G | tm0 A1:B1 | tm0 A1:G | tm0 A1:Gtm0 |
|---|---|---|---|---|---|---|---|---|
| HumanEval/13 | 111 | 4/4 | 206/207; 206/207 | 3 | @111 | = | @84 | = |
| HumanEval/35 | 102 | 4/1 | 216/217; 216/217 | 3 | @102 | = | = | = |
| HumanEval/55 | 72 | 4/4 | 153/154; 153/154 | 3 | @72 | = | @72 | = |
| HumanEval/59 | 102 | 4/3 | 197/198; 197/198 | 7 | @102 | = | @94 | = |
| HumanEval/91 | 119 | 4/2 | 254/255; 255/256 | 12 | = | = | @119 | @121 |
| HumanEval/101 | 121 | 4/4 | 266/267; 263/264 | 3 | @121 | = | @121 | = |
| HumanEval/148 | 27 | 8/4 | 265/266; 267/268 | 3 | @27 | = | @27 | @27 |
| mtbench-101 | 65 | 4/1 | 114/115; 114/115 | 1 | @65 | = | @62 | = |
| mtbench-105 | 100 | 4/2 | 320/321; 320/321 | 0 | @100 | = | @5 | @56 |
| mtbench-115 | 39 | 4/4 | 124/125; 124/125 | 1 | @39 | = | @15 | = |
| mtbench-121 | 93 | 4/3 | 128/129; 129/130 | 1 | @93 | = | @124 | = |
| mtbench-129 | 14 | 4/3 | 56/57; 56/57 | 1 | @14 | = | @47 | = |
| mtbench-136 | 30 | 3/4 | 299/300; 299/300 | 0 | @30 | = | @9 | @9 |

**Conteggi sul sottoinsieme da 19 (code/chat):**
- v3: A1:B1 6/19, A1:G 6/19, B1:G 15/19.
- TILED_MM=0: A1:B1 18/19 (residuo mtbench-132), A1:G 6/19, B1:G 6/19, A1:Gtm0 14/19, B1:Gtm0 15/19, Gtm0:G 7/19.
- A1_tm0 vs A1 di default: 8/19.

**A1_tm0 contro Gtm0** (5 divergenze: HumanEval/91 @121, /148 @27, mtbench-105 @56, -132 @64, -136 @9):
- Il greedy ha sempre T=1, il braccio T=4 o T=8.
- Gap del braccio: 0.00123–0.20959. Gap del greedy: 0.04515–0.13823.
- Sempre top-1/top-2 scambiati, ciascuno emette il proprio top-1. File: `tm0_div_logits_<ET>.json`.

## Controlli (punti 1–4 del piano Lead)

1. **Greedy puro senza draft** (base_r1, base_r2, `--mode base`, stessi binario e flag, -t 6):
   - 19/19 e 8/8 output identici fra i due rilanci e con TF3.
   - 2152/2152 e 1024/1024 round con vmargin bit-identici.
   - Nella v3, quasi sempre è A1 a staccarsi dal greedy: B1:G 15/19, A1:G 6/19.
2. **Ripetibilità:**
   - A1 rilanciato 2 volte: 19/19 e 8/8 output, 632/632 e 265/265 round bit-identici alla v3.
   - B1 rilanciato 2 volte: 19/19 e 8/8 output, 711/711 e 284/284 round bit-identici.
   - Le run sono deterministiche: niente race né non determinismo dei thread.
3. **Batch di verifica fissato (ywrong/yright/mtp_cap3):** non eseguito. La passata ywrong_d3, avviata alle 15:12:13 CET, è stata interrotta alle 15:12:17 CET per dare priorità alla prova TILED_MM=0; i file `*.interrotto` non sono usati. Al suo posto è stata fatta la prova TILED_MM=0.
4. **Logit alla prima divergenza v3** (vmargin del round più vmargin batch 1 di base_r1):
   - code/chat A1:B1: n=39 valori; <0.05: 14; 0.05–0.5: 25; ≥0.5: 0. Min 0.00562, mediana 0.10691, max 0.38187.
   - code/chat A1:G: n=39, max 0.38187.
   - code/chat B1:G: n=12, max 0.35687.
   - Edit: A1:B1 max 0.36271, B1:G max 0.44916.
   - Token emesso ≠ top-1: 0. Violazioni del criterio BUG: 0.
   - Pre-criterio: c'è una quota rilevante nella fascia 0.05–0.5, cioè né quasi-pareggio stretto né bug. Il fatto che i logit cambino con il percorso di kernel (sopra) è compatibile con un effetto numerico.
- **Effetto misurato della variabile:** fra aprime_rr1 (default) e aprime_tm0, sui round con lo stesso input prima della divergenza di output, i vmargin identici sono:
  - code/chat: 0/224 (T<8) e 0/41 (T≥8);
  - edit: 0/110 e 0/31.
  - Per B1, 0/239 e 0/96.
  - Esempio, round 0 di HumanEval/2: gap 5.12799 → 5.03584.
  - **Ipotesi, non verificata:** il prefill (righe ≥ 8) passa dal tiled, quindi con TILED_MM=0 cambia tutto lo stato da subito. Ne segue che la prova TILED_MM=0 non isola solo i round T=8.

## mtbench-105 e mtbench-136: celle KV, n_kv/nek1, FA

| caso | posizione | T | celle (kv_pos/ctx_len) |
|---|---|---|---|
| v3, prima differenza numerica (Policy) | 105 pos 75; 136 pos 24 | A1 4 / B1 1 | 296/297; 295/296 |
| v3, prima differenza di output | 105 pos 100; 136 pos 30 | 4/2 e 3/4 | 320/321; 299/300 |
| TILED_MM=0, A1:B1 | identici | — | — |
| TILED_MM=0, A1_tm0 vs Gtm0 | 105 @56; 136 @9 | 4 / 1 | 277/278; 278/279 contro 280/281 |

- **n_kv / nek1: 512 in tutti i casi sopra. Dedotta, non misurata.**
  - Formula: `llama_kv_cache::get_n_kv` (`src/llama-kv-cache.cpp` L1285-1298) = max(256, GGML_PAD(used_max_p1, 256)), limitato a 8192. Celle fra 257 e 512 danno 512.
  - Il valore non è leggibile senza nuovi lanci: `LLAMA_LOG_DEBUG` con n_kv in `src/llama-graph.cpp` L454 richiede -v. Nessuna rebuild né lancio fatto.
  - Il percorso split-KV di FA (`ggml/src/ggml-cpu/ops.cpp` L9585-9586) richiede `neq1==1` (una sola riga di query, cioè un round con T=1), K/V f16/f32 e `nek1 >= 512`. Chunk = ceil(512/6) = 86 (L9589).
  - Quindi, se FA è attiva, la condizione nek1 ≥ 512 è soddisfatta **solo nei round con T=1** (in v3 il braccio B1 a pos 75/24; in tm0 il greedy). È coerente con il candidato "FA split-KV", ma **non dimostrato**: caso aperto.
- **Stato FA: non determinato dai log.** I log delle run non sono verbosi. Il default è `-fa auto` (`common/common.h` L506), risolto da probe in `src/llama-context.cpp` L322-323 e L659-661 (Policy lo deduce attivo). Il lancio breve -v non è stato fatto (budget).
- **Le posizioni 75/24 riportate da Policy sono corrette** nella sua definizione (prima differenza numerica). Il kernel GDN non è citato come causa (ipotesi ritirata).

## Ambiente effettivo dei processi (da /proc/<pid>/environ, `proc_environ_tm0.log`)

- Tutti e 6 i processi della prova risultano con `GGML_CPU_TILED_MM=0` e nessun'altra variabile GGML_*. **GGML_CPU_TILED_MM_FORCE è assente** (0 occorrenze):
  - aprime_tm0, pid 780678;
  - aprime_tm0_<ET>, pid 810998;
  - default_a_tm0, pid 820196;
  - default_a_tm0_<ET>, pid 830891;
  - base_tm0, pid 832166.
- Lo script fa `export GGML_CPU_TILED_MM=0` (riga 20) e non imposta FORCE.
- **Come viene letta la variabile:**
  - `ggml/src/ggml-cpu/tiled/tiled.cpp` L572-581: `getenv("GGML_CPU_TILED_MM")`, `enabled = env==NULL || atoi(env)!=0`, letta una volta sola (std::call_once). Con 0 il tiled è disabilitato.
  - L607 e L648: con il tiled disabilitato ritorna false e si passa al mul_mat vec_dot (`ggml-cpu.c` L1269).
  - L1202-1205: soglia `rows >= 8`. Copre Q4_K/Q5_K/Q6_K (L617-619, L1171-1175).
  - La stringa è presente in `libggml-cpu.so.0.27.0` (31e0c411…), caricata dal binario.

## Sovrapposizioni e cronologia (CET)

- **diag_greedy_aprime:** START 14:49:19.
  - 12/20 passate ok (il log dice per errore "11/20"): base_r1/r2, aprime_rr1/rr2, default_a_rr1/rr2, ×2 set.
  - Interrotta alle 15:12:17 dopo default_a_rr2_<ET> per la prova TILED (priorità Lead).
- **diag_tiled_mm0:** START 15:12:38. aprime_tm0, default_a_tm0 (+<ET>) ok; ultimo .ok alle 16:13:36.
  - base_tm0 (code/chat, 19 prompt) è partito alle 16:13:36 nonostante lo stop deciso per budget (il kill è fallito) ed è arrivato a termine alle 16:15:57.
  - 19/19 request, riga finale del tracer presente, exit code non registrato: **non è il set da 60**.
  - Uso solo descrittivo, non per i verdetti (`base_tm0.ok.orfano`). base_tm0 <ET> non eseguito.
- **Sovrapposizioni con Policy:**
  - logit_probe di Policy (pid 758319, nice 10): il mio processo base_r1 (pid 755243) è stato in pausa (SIGSTOP) dalle 14:56:10 alle 14:56:30. Il log lo etichetta per errore "base_r1 edit".
  - **rollback_probe di Policy 15:15:51-16:11:38** (ps lstart / `cpu_busy_policy.log`), in parallelo con aprime_tm0, aprime_tm0_<ET> e default_a_tm0 (15:12:38-16:12:25). Il mio processo è stato in pausa 15:29:38-15:36:14, poi ha girato in sovrapposizione.
  - Build Policy/Scout in parallelo.
  - **I confronti di output e logit restano validi** (le run sono deterministiche bit per bit, controllo 2). **I tempi non sono usabili.**

## Comandi, versioni, sha256

- **Hardware:** Intel Xeon (8 CPU, 1 thread/core), Linux 6.12.94+, -t 6, nice 19.
- **Software:** llama.cpp d327bf1f0780f87b8c01b367b61853b0c291d7c4 con patch locali (common/speculative.*). Build `build-nollamafile` (Release, GGML_LLAMAFILE OFF, GGML_NATIVE ON).
- **Flag:** comuni a tutti `-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --spec-draft-n-max 3`.
  - A1: `--mode live --live-src aprime --ref REF --dmax 7`.
  - B1: `--mode live --live-src default_a --ref REF --dmax 7`.
  - G: `--mode base --dmax 7`.
  - Prova tiled: env `GGML_CPU_TILED_MM=0`.
  - Comandi completi con orari in `diag_greedy_aprime_v1/cmds_<ET>.txt`.
- **Input:**

  | file | sha256 |
  |---|---|
  | binario `proxy/llama_spec_trace.v14.nollamafile` | e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e |
  | modello | 18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b |
  | REF ref_holdout_tf.tsv (generato con build LLAMAFILE ON, diversa dai bracci) | 0a86e4679f75c4a2aaf1361d7d1b742d374ac7489aae82daf93a3e349c040a9d |
  | libllama-common | ef3d929534cecb1c60dcb5953bb44452a75a6b91dd69cb2b09569dbde51d59f7 |
  | libggml-cpu | 31e0c41168c05450f378dde3f223a671f5d13781988409c2f1a8bf80fb738f96 |
  | tiled.cpp | a5d92ce8f617696778e225de6658180649143fec3792c5cfef84170641f2d06e |
  | prompts.jsonl | 5fbfc1f00b1f408bd1e853e04c71622e362cfb74c9314ccf0749525412478a8e |

- **Script e tool:**

  | file | sha256 |
  |---|---|
  | `runs/run_diag_greedy_aprime_v1.sh` | 2b63ef1f46f410717d3e0d01f251571d9b5cbd342a60304f7b86451751f894d6 |
  | `runs/run_diag_tiled_mm0_v1.sh` | 90c633da733554f71403bb22b2b6996fd45f3419bac061a06a1cbf0164854385 |
  | `tools/diag_greedy_aprime_report.py` | 584fea4c8c6c4e1913218cb564b2463f462ea45c5d0399eefe27d426a697dcc4 |
  | `tools/diag_tiled_mm0_report.py` | 64bc871acdd251f58a7b949c20e3940912aabe226f0fd94fd369d79cdbe75f49 |
  | `tools/diag_greedy_aprime_analyze.py` | 45123247794ada0d482c111cf44203b7983cb475dee6a6af9c0c05f0b82dc258 |

- **Previsioni:**

  | file | sha256 |
  |---|---|
  | v1 | 2a882b80bb6fe49ae8051bf67b224f0ba78ab2e582c84b08a0017a670aa41df9 |
  | v2 (Lead) | f26643daec7b7216af2b20cf8984d885139f9d64f977c7441f78f126cc658faf |
  | fa-off (non usata) | 95e6e724b060dd59c950ba8bd2f3ecfe525ac5de12d2d7a4385a6f064b362d8b |

- **Dati grezzi e json:** `runs/diag_greedy_aprime_v1/`, con sha in `MANIFEST.sha256`.

## Limiti

- Sottoinsiemi: 19 prompt code/chat e 8 edit, non i 90.
- Greedy con TILED_MM=0 solo code/chat e solo descrittivo.
- Controllo 3 (batch fissato) non eseguito.
- Braccio -fa off, lancio -v per FA e n_kv, e controllo "arbitro con fonte fissa": non eseguiti.
- n_kv dedotta dal codice. FA non determinata.
- REF di v3 da build diversa.
- Tempi non validi.
