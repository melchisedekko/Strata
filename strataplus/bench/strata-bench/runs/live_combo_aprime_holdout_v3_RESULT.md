# RESULT — run (a′) v3, live con arbitro, holdout 90, A/B tok/s a coppie alternate
**Etichetta: proxy CPU, non AMD, llama.cpp non Strata.** Scritto il 27/10/2026 alle 14:4x CET (UTC+1). Tutti gli orari sono CET (UTC+1).
Dominio edit: etichetta pubblica `edit_np`, tag dei file `<ET>`. Qui ci sono solo aggregati, nessun id per richiesta.

## Esito
**NO-GO-proxy, stop per la regola (ii).** Il controllo greedy dopo B1 ha trovato output diversi fra A1 e B1, e lo script si è fermato come previsto
(`campaign.log` 14:31:39 CET: `FAILED aprime_ab_v3: greedy diverso o errore (aprime_r1), STOP (regola ii)`; file `STOPPED_greedy`).
- **P0 non è bocciata.** Resta in coda AMD senza GO-proxy (regola (iv)). Su AMD decide il criterio dell'output identico al 100%.
- (i), (iii) e (iv) **non valutabili**. Gli step validity, aprime_post, toks_ab e decide (script L94-104) non sono stati eseguiti, quindi non ci sono
  AL live, scarto dal riferimento di Policy, coerenza dell'arbitro, tok/s, delta o IC95. Il riferimento `POLICY_REPLAY_REF` era nell'ambiente del processo
  (con `POLICY_REPLAY_REF_SHA256` = cfc9da83…), ma non è stato letto.
- **Ricalcolo informativo dell'AL sul TF cap 3: saltato per decisione di Lead (27/10 14:36 CET).**
- Codice di uscita: `exit 1`, ricavato dal percorso dello script (L82, `gcheck`) e dalla riga FAILED. `run_v3_nohup.log` è vuoto (0 byte).
- Finestra in `cpu_busy_bench.log`: 13:45:14 → 14:31:39 (riga END scritta dal Lead alle 14:36).

## Passate eseguite (campaign.log, START/END)
| passata | START | END | durata | exit |
|---|---|---|---|---|
| TF cap 3 codechat (`holdout_tf_cap3_v14`) | 13:45:46 | 14:03:03 | 17 min 17 s | 0 |
| TF cap 3 edit (`holdout_tf_cap3_v14_<ET>`) | 14:03:33 | 14:13:03 | 9 min 30 s | 0 |
| A1 codechat (`aprime_r1`) | 14:13:33 | 14:18:47 | 5 min 14 s | 0 |
| A1 edit (`aprime_r1_<ET>`) | 14:19:17 | 14:22:09 | 2 min 52 s | 0 |
| B1 codechat (`default_a_r1`) | 14:22:39 | 14:28:07 | 5 min 28 s | 0 |
| B1 edit (`default_a_r1_<ET>`) | 14:28:38 | 14:31:39 | 3 min 01 s | 0 |
| greedy A1 vs B1, codechat | 14:31:39 | 14:31:39 | — | 1 → STOP |
Non eseguiti: B2, A2, A3, B3, B4 e A4; greedy edit; validity; post; A/B; decide; MANIFEST dello script (`MANIFEST_<ET>.sha256`); `aprime_ab_v3.done`.

## Greedy (ii): misure
- **Codechat, A1 vs B1** (`greedy_aprime_r1_codechat.json`): **47/60 identici (78,3%)**, 13 diversi, 0 mancanti.
  - 7 code: HumanEval/13, HumanEval/35, HumanEval/55, HumanEval/59, HumanEval/91, HumanEval/101, HumanEval/148
  - 6 chat: mtbench-101, mtbench-105, mtbench-115, mtbench-121, mtbench-129, mtbench-136
- **Edit, A1 vs B1** (confronto diretto in sola lettura, eseguito dopo lo stop; lo script non è arrivato al controllo edit): **7/30 diversi**. Solo aggregato.
- **Posizione della prima divergenza A1/B1** (indice 0-based del token di output, n_predict 128):
  - codechat (13 prompt): **mediana 93**, min 14, max 121. Valori ordinati: 14, 27, 30, 39, 65, 72, 93, 100, 102, 102, 111, 119, 121.
  - edit (7 prompt, aggregato): mediana 69, min 9, max 101. Su tutti i 20 prompt diversi la mediana è 75,5.
- **Confronti con il TF cap 3 e con il riferimento greedy** (`ref_tokens` = `ref_holdout_tf.tsv`, in sola lettura):
| confronto | codechat | edit (aggregato) |
|---|---|---|
| B1 = TF cap 3 | 56/60 | 23/30 |
| A1 = TF cap 3 | 47/60 | 23/30 |
| A1 = riferimento greedy | 32/60 | 24/30 |
| B1 = riferimento greedy | 28/60 | 24/30 |
| TF cap 3 = riferimento greedy | 28/60 | 23/30 |

## Contaminazione CPU
Fonte: `tools/cpu_judge.py` (8fb3e560…) sui `cpu_*.log`, monitor ogni 2 s, escluso sand-host. Per le passate live è il valore di `campaign.log`.
Le due passate TF cap 3 sono state rivalutate in sola lettura con cpu_judge (27/10 14:4x CET, nice 19) e coincidono con `campaign.log`.
| passata | intervalli ≥0,5 core estranei | picco (core) |
|---|---|---|
| TF cap 3 codechat | 1 | 0,533 |
| TF cap 3 edit | 0 | 0,299 |
| A1 codechat | 0 | 0,189 |
| A1 edit | 0 | 0,15 |
| B1 codechat | 0 | 0,165 |
| B1 edit | 0 | 0,165 |

## Spiegazioni possibili: entrambe NON verificate e fuori da questa coda
- **(a) NON verificata:** quasi pareggi in virgola mobile che dipendono dalla dimensione del batch di verifica su CPU. I due bracci verificano bozze
  di lunghezza diversa, quindi i logit possono cambiare di poco e invertire un argmax quasi pari.
- **(b) NON verificata:** un bug dell'arbitro o del tracer.
Nessun esperimento è stato fatto per distinguerle.

## In coda per dopo il blocco (NON aprire ora)
- Su AMD il passo zero dovrà includere un controllo di identità greedy controllo vs controllo con batch di verifica diversi, prima di qualsiasi A/B.

## Comandi (cmds_<ET>.txt; tutti `nice -n 19`)
Lancio: `cd /workspace/strata-bench && nohup bash runs/run_live_combo_aprime_holdout_v3.sh &`, avviato alle 13:45:14 CET (PID bash 715879),
con `POLICY_REPLAY_REF` e `POLICY_REPLAY_REF_SHA256` nell'ambiente.
`FL = -m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7 --spec-draft-n-max 3`
- TF: `./proxy/llama_spec_trace.v14.nollamafile $FL --prompts <P> --mode tf --live-src mtp --tag holdout_tf_cap3_v14[_<ET>] --out …`
- A: `… $FL --prompts <P> --mode live --live-src aprime --ref …/holdout_lookup_v12/ref_holdout_tf.tsv --tag aprime_r1[_<ET>] --out …`
- B: `… $FL --prompts <P> --mode live --live-src default_a --ref …/holdout_lookup_v12/ref_holdout_tf.tsv --tag default_a_r1[_<ET>] --out …`
- greedy: `python3 tools/aprime_toks_ab.py greedy greedy_aprime_r1_codechat.json aprime_r1.jsonl default_a_r1.jsonl` → exit 1
- `<P>` = `datasets/holdout_90_codechat.jsonl` (30 code + 30 chat), poi `datasets/holdout_90_<ET>.jsonl` (30 edit).

## Hardware e versioni (build_env_info_<ET>.txt, 13:45:16 CET)
- VM KVM, Intel Xeon Processor (family 6, model 207), 8 vCPU (1 thread/core), AVX-512/AMX, 16002 MB RAM, nessuno swap. Kernel Linux 6.12.94+ x86_64.
  Loadavg all'avvio 0.28 0.35 0.42.
- gcc 14.2.0 (Debian 14.2.0-19), cmake 3.31.6, Python 3.13.5.
- llama.cpp `d327bf1f0780f87b8c01b367b61853b0c291d7c4`, 2 file modificati. Build `build-nollamafile`: Release, GGML_LLAMAFILE=OFF, GGML_NATIVE=ON.
- Processo llama: `-t 6`, nice 19, un solo processo alla volta. `STRATA_DRAFT_VOCAB` tolto dall'env.

## sha256 degli input
Verificati dallo script all'avvio (`sha256sum -c`, L27-45: superato, altrimenti la run non sarebbe partita):
| input | sha256 |
|---|---|
| runs/run_live_combo_aprime_holdout_v3.sh | 11433cdfd87ed0e5da6e75a2d301e86562caa595a1f8464006912d42d8eb72fd |
| proxy/llama_spec_trace.v14.nollamafile | e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e |
| proxy/llama_spec_trace_v14.cpp | ddea7320ba99054810275d0228c89d1d0b93abd7ab0e1e5584507e739b048283 |
| proxy/strata_arbiter_v1.hpp | 85bb5341d9995d495bd2dd72ba52349ccccbed4497eeb00da67e1b500d8e7c19 |
| proxy/strata_arbiter_v1.py | 2b0e8b9a0c45d6927dca09db8f352a288305f5521e0c874ff45d4c87bf46611a |
| datasets/holdout_90.jsonl | 739fbb9c606c881122f1426091aa47dc7f59873176405951b2e7aa7b0febdcb3 |
| datasets/holdout_90_codechat.jsonl | 18288525fff122efc9790efbeadcbf810ae5c650149833ea5cb8a141efdba84e |
| datasets/holdout_90_<ET>.jsonl | 6b2404c8b4d5de552c8faf1f27dc09d2b59ceb62721d5a76f5a769c1ed2739f2 |
| traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv | 0a86e4679f75c4a2aaf1361d7d1b742d374ac7489aae82daf93a3e349c040a9d |
| traces/raw/v11_holdout/holdout_tf_d7.jsonl | a16cf384f1dc5c06cbb5ae544051293413fa016fc3a1710401fad62b6ccad854 |
| build-nollamafile/bin/libllama-common.so.0.7.0 | ef3d929534cecb1c60dcb5953bb44452a75a6b91dd69cb2b09569dbde51d59f7 |
| models/qwen35-2b-mtp-q4_k_m.gguf | 18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b |
| traces/mtp_cap_prefix_check.json | 349866f270653c9fdced2e8a13a6b9fe94f1f0136aeb015b8c30640acb002ef2 |
| tools/mtp_cap_prefix_check.py | 42dd8621503ef07dbea6e34d1ca22791e001fed95062d7970898a81b6fc8b993 |
| tools/aprime_post.py | 808ebcc95997fef256bb4f3642f5740ff2aa6c4755a3c34750c20eecaab82e3e |
| tools/aprime_toks_ab.py | 7e1a2dcdd757421bed5939878f5647d42e792f68a5540aa0cafd3cc51eddb0fc |
| tools/cpu_foreign.py | f4276c7bcb733f7013f8b52854e010c7a456e9f029c6a950cb36eedd53fb2263 |
| tools/cpu_judge.py | 8fb3e560689cd6784235feb2e899f63fec164a7324a2cee1e5a196459c6c027f |
Altre librerie registrate: libllama.so 89f735fb…, libggml.so d7c4c887…, libggml-base.so 75b39048…, libggml-cpu.so 31e0c411….
Run file della v3: `runs/live_combo_aprime_holdout_v3.md` 2b01dae92a648de2c3bfeee0c07eb3f0aed85318a0f6f5f9708d2ba565015376.
Riferimento di Policy (passato ma non letto, perché la run si è fermata prima di decide):
- `strata-policy/replay/results/aprime_ref/aprime_ref_AL_<ET>.json` cfc9da837c6cd7de48fd31f0f6f13badda40f5d433e14e98afc9937ba8d3d003
- run file `run_aprime_live_ref_v2.json` 672bba2ca0c436872fcd2bc95657da5b8d584fef5c4613700595c0098fdea1ac
- script `aprime_live_ref_v2.py` c811322f58ba368d95c46397ae53010d9995e913f9ba0ac24cb6f8ae7f56d2e6

## sha256 degli output
Cartella `/workspace/strata-plus/traces/raw/aprime_holdout_v14_ab/`. `MANIFEST.sha256` (31 file, scritto il 27/10 alle 14:37 CET, read-only) ha sha256
**f133f77ac851a54e7f888ffa6dad450e68228ff61da62cf5a51e52aeaa860b3d** (anche in `MANIFEST.sha256.sha256`). I nomi dei file edit nel manifest contengono `<ET>`.
| file | sha256 |
|---|---|
| holdout_tf_cap3_v14.jsonl | 5ac2ac45135604892089b29ab6b987f28d1777886def17d41bdca2b9ca7ba02a |
| holdout_tf_cap3_v14_<ET>.jsonl | 70cad8177e4992a16c6b95a17068e352fecb4b819fc26a47d0397843b7005091 |
| aprime_r1.jsonl | 58dd282258b4c46019d6ed4acc41fdf1f63834efa9e61cf7047209538af11b79 |
| aprime_r1_<ET>.jsonl | cc569574396fcac1722e914ddb237caa4792b8c425c5fd009d0b900026b63aaa |
| default_a_r1.jsonl | c1c3d9198b1905be5b7dd89824b92b0e2535e895bc0838e6befae92ba6fe8ba7 |
| default_a_r1_<ET>.jsonl | f247189ffc1b32a60b815d893c1443cebea7cc25c00543477a6b2e080603b627 |
| greedy_aprime_r1_codechat.json | 12ae90ae56629f697ce4ad8216e13df59d4646c74ca9fe3a9c650aadd01edef6 |

## Limiti
- **proxy CPU, non AMD, llama.cpp non Strata.** Tracer v14 su CPU, 6 thread, nice 19. Nessun numero AMD. Il GO-proxy, che comunque qui non c'è, non vale come GO di P0.
- **Prefix check del cap:** `mtp_cap_prefix_check.json` all_pairs dà 5210 coincidenti su 5389 (0,966784), all_100pct false
  (`cap_precheck.txt`: `5210 5389 False`). Per questo il TF cap 3 è stato rigenerato (fase 0).
- I 4 limiti dichiarati da Policy per il riferimento (`strata-policy/replay/results/aprime_ref/REPORT.md`, sez. Limiti 1-4):
  1. tf_d7 non è cap 3: i candidati MTP sono i primi 3 dei 7 token del TF d7 (troncamento). La proprietà di prefisso non vale al 100% (5210/5389).
  2. È un proxy: CPU, non AMD; llama.cpp, non Strata; l'arbitro è una copia di DraftPolicy. L'accettazione è ricostruita assumendo il live greedy-identico a y,
     cioè proprio il controllo (ii) di Bench, che qui **non** è superato.
  3. La contaminazione è irrilevante per l'AL di riferimento, che non dipende dai ms.
  4. s(T) parametrica fissata al default kShape. Su AMD choose usa l'EMA dei tempi, quindi le scelte possono cambiare. Le probabilità MTP non contano in (a′) (spec_min_p = 0).
- I confronti edit e le posizioni di divergenza sono stati calcolati da Bench in sola lettura dopo lo stop (python a nice 19, nessun file scritto).
  Non vengono da uno step dello script.
- Una sola ripetizione per braccio: nessuna stima di varianza fra ripetizioni.
