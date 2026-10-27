# arbiter_divergence_v1 — divergenze greedy A1 vs B1 (Bench v3 (a′)): bug o quasi-pareggi FP?
**Proxy CPU, non AMD, llama.cpp non Strata.** Strata Policy, 2026-10-27 CET. Dati: `/workspace/strata-plus/traces/raw/aprime_holdout_v14_ab/` (sola lettura),
A1=`aprime_r1.jsonl`, B1=`default_a_r1.jsonl`, TF=`holdout_tf_cap3_v14.jsonl`. Criteri preregistrati in `/workspace/policy-local/arbiter_diag/PREREG.md`
(sha256 52ba787736bf8e144f3ac371a5af4b6e383b9a24b2be3def579e5766c4e0d455, 444, scritto 14:46:30 CET prima di guardare i margini nei punti di divergenza).
Questo file: solo code/chat. Aggregati edit_np nel file companion con lo stesso prefisso.

## Verdetto
- **Lettera del PREREG (forme i, ii, iii): `bug`** — il criterio BUG ("token di A1 non top-1 in nessuna forma testata") scatta su **7/13** prompt code/chat
  (HumanEval/35, /55, /101, mtbench-101, -105, -121, -129); FP 5/13, indeterminato 1/13 (HumanEval/91).
- **Nessun difetto di codice localizzato.** Il criterio scatta perché le forme (ii)/(iii) ("da zero" con la forma del batch di verifica del solo round in d)
  non riproducono lo stato numerico che A1 aveva davvero: il logit in d dipende dall'intera storia di scomposizione in batch (prefill + round + rollback
  dello stato ricorrente), non solo dalla forma del batch di verifica di quel round.
- **Forma aggiuntiva NON preregistrata (iv)/(v)** = replay esatto della storia di A1/B1 (stessi batch, stessi `seq_rm`, come il tracer): riproduce **tutti**
  i vmargin loggati (2328 righe code/chat, 0 top-1 diversi, |Δgap| max 5e-6 = precisione di stampa). In (iv) il token di A1 è top-1 **13/13**, in (v)
  quello di B1 è top-1 **13/13**; margine in d forma (i) max 0.2826 < τ; nessun margine > 10·τ. Con (iv)/(v): **13/13 FP, 0 BUG → "nessun bug trovato"**,
  ma questo verdetto usa una forma non preregistrata: decisione al proprietario (proposta: PREREG v2 con (iv)/(v) e verifica su una run nuova).
- T1: 0 violazioni degli invarianti, decisioni dell'arbitro ricostruite identiche al 100%.

## Soglia τ (prompt non divergenti, fissata prima di T2 sulle divergenze)
Prompt (primi 5 in ordine di file, A1=B1, ≥40 token): HumanEval/2, /28, /30, /34, /52; 482 posizioni (righe j < committed dei round di A1).
|Δlogit top-1| forma (i) vs (ii): **τ = max = 0.566763**, **p99 = 0.444130**, mediana 0.108244; 5/482 esattamente 0. (Δ del gap top1-top2 con stesso top-2: max 0.868799, p99 0.650185.)
Aggiunta non preregistrata, (i) vs (iv) (storia reale di A1 con rollback), stesse 482 posizioni: max 0.545629, p99 0.442425, mediana 0.078430
→ la storia con rollback non devia più della sola forma del batch senza rollback. (iv) vs log di A1 su questi prompt: 523 righe, 0 top-1 diversi, |Δgap| max 5e-6.
Validazione del probe: forma (i) vs vmargin della run TF sugli stessi 5 prompt: 482 righe, 0 top-1 diversi, |Δgap| max 5e-6.

## T1 — arbitro e invarianti (solo tracce)
| traccia | dominio | round | decisioni identiche | violazioni |
|---|---|---|---|---|
| A1 | code | 785 | 785 (100%) | 0 |
| A1 | chat | 1342 | 1342 (100%) | 0 |
| B1 | code | 905 | 905 (100%) | 0 |
| B1 | chat | 1606 | 1606 (100%) | 0 |
Campi confrontati: T, lookup, gate, t_mtp, T_pre_room (replay `proxy/strata_arbiter_v1.py` con observe() round per round). 0 valori min_p entro 1e-5 dalla soglia.
Nota: la prima versione segnalava casi con EOG accettato a metà proposta seguito da stop; è la regola di `common_sampler_sample_and_accept_n`
(`common/sampling.cpp` L708, interruzione su EOG accettato se i+1 < draft.size()), non un bug; modellata nello script (EOG = 248044, 248046, 248063, 248064, 248065, letti dal GGUF).

## T2 — per prompt (code/chat). Celle: top-1 (=A token di A1, =B token di B1) / margine top1-top2 in logit, nella posizione che predice d
(i) prefill + decodifica a batch 1; (ii) da zero, prefill di contesto fino a pos del round + batch [ultimo token + proposal] del round di A1 che contiene d;
(iii) idem B1; (iv) storia esatta di A1 (non preregistrata); (v) storia esatta di B1 (non preregistrata).

| prompt | d | tok A1 | tok B1 | (i) | (ii) | (iii) | (iv) | (v) | verdetto PREREG (i–iii) | verdetto con (iv)/(v) |
|---|---|---|---|---|---|---|---|---|---|---|
| HumanEval/13 | 111 | 11848 | 292 | 292=B / 0.1318 | 11848=A / 0.0014 | 11848=A / 0.0014 | 11848=A / 0.0235 | 292=B / 0.1318 | FP | FP |
| HumanEval/35 | 102 | 506 | 264 | 264=B / 0.2826 | 264=B / 0.2646 | 264=B / 0.2646 | 506=A / 0.0252 | 264=B / 0.2826 | BUG | FP |
| HumanEval/55 | 72 | 4265 | 413 | 413=B / 0.1222 | 413=B / 0.0917 | 413=B / 0.0917 | 4265=A / 0.0556 | 413=B / 0.1222 | BUG | FP |
| HumanEval/59 | 102 | 1716 | 21078 | 21078=B / 0.2552 | 1716=A / 0.0104 | 1716=A / 0.0104 | 1716=A / 0.3819 | 21078=B / 0.2552 | FP | FP |
| HumanEval/91 | 119 | 585 | 653 | 585=A / 0.0245 | 653=B / 0.0122 | 653=B / 0.0862 | 585=A / 0.1748 | 653=B / 0.1069 | INDET. | FP |
| HumanEval/101 | 121 | 653 | 460 | 460=B / 0.0550 | 460=B / 0.1245 | 460=B / 0.0290 | 653=A / 0.1189 | 460=B / 0.0314 | BUG | FP |
| HumanEval/148 | 27 | 17554 | 11784 | 11784=B / 0.0195 | 17554=A / 0.0039 | 11784=B / 0.0712 | 17554=A / 0.3266 | 11784=B / 0.0473 | FP | FP |
| mtbench-101 | 65 | 2302 | 561 | 561=B / 0.0076 | 561=B / 0.0376 | 561=B / 0.0376 | 2302=A / 0.0091 | 561=B / 0.0076 | BUG | FP |
| mtbench-105 | 100 | 11 | 25 | 25=B / 0.2048 | 25=B / 0.0740 | 25=B / 0.0740 | 11=A / 0.0357 | 25=B / 0.0639 | BUG | FP |
| mtbench-115 | 39 | 332 | 16 | 16=B / 0.0180 | 332=A / 0.3941 | 332=A / 0.3941 | 332=A / 0.1951 | 16=B / 0.0180 | FP | FP |
| mtbench-121 | 93 | 1844 | 318 | 318=B / 0.1158 | 318=B / 0.4187 | 318=B / 0.3488 | 1844=A / 0.0056 | 318=B / 0.1158 | BUG | FP |
| mtbench-129 | 14 | 314 | 440 | 440=B / 0.0729 | 440=B / 0.0500 | 440=B / 0.0500 | 314=A / 0.0484 | 440=B / 0.0729 | BUG | FP |
| mtbench-136 | 30 | 11 | 10629 | 10629=B / 0.2123 | 11=A / 0.0383 | 11=A / 0.0383 | 11=A / 0.2607 | 10629=B / 0.1558 | FP | FP |

Conteggi top-1 = token A1 / token B1: (i) 1/12, (ii) 5/8, (iii) 4/9, (iv) 13/0, (v) 0/13. HumanEval/91 è INDET. per la lettera: il token di A1 è top-1 in (i) (forma non usata da A1) ma non in (ii).
Tutti i 13 punti sono scambi top-1/top-2 fra i due token; margine forma (i): min 0.0076, max 0.2826 (< τ = 0.5668).

## Comandi
- T1: `cd /workspace/strata-plus/traces/raw/aprime_holdout_v14_ab; nice -n 10 python3 /workspace/strata-policy/diag/t1_arbiter_invariants.py /workspace/policy-local/arbiter_diag/t1_perprompt.json aprime_r1.jsonl default_a_r1.jsonl <A1 edit_np>.jsonl <B1 edit_np>.jsonl` (gli ultimi due: tracce edit_np, nomi nel MANIFEST della run)
- Probe (sorgente `diag/logit_probe.cpp`, build: `c++ -std=c++17 -O3 -DNDEBUG -DGGML_BACKEND_SHARED -DGGML_SHARED -DGGML_USE_CPU -DLLAMA_SHARED -I$L/common -I$L/vendor -I$L/include -I$L/ggml/include logit_probe.cpp -L$B/bin -lllama-common -lllama -lggml -lggml-base -Wl,-rpath,$B/bin`, L=/workspace/llama.cpp, B=$L/build-nollamafile, stessa build della run).
- Job: `python3 diag/make_jobs.py tau aprime_r1.jsonl default_a_r1.jsonl jobs_tau.txt 5 40`; `make_jobs.py div aprime_r1.jsonl default_a_r1.jsonl jobs_div_codechat.txt`; `make_jobs.py tauhist ... jobs_tauhist.txt 5 40`
- Esecuzione (da /workspace/strata-bench): `nice -n 10 logit_probe -m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --spec-draft-n-max 3 --dmax 7 --jobs <jobs> --out <probe.jsonl>`
  — **-t 6** (come la run, per riprodurre la forma numerica; annotato in cpu_busy_policy.log).
- Analisi: `t2_analyze.py tau probe_tau.jsonl jobs_tau.txt.meta.json t2_tau.json`; `t2_analyze.py div probe_div_codechat.jsonl jobs_div_codechat.txt.meta.json 0.5667629999999981 t2_div_codechat.json holdout_tf_cap3_v14.jsonl`;
  `tauhist_analyze.py probe_tau.jsonl probe_tauhist.jsonl jobs_tau.txt.meta.json aprime_r1.jsonl t2_tauhist.json`; `check_probe_vs_tf.py holdout_tf_cap3_v14.jsonl probe_tau.jsonl jobs_tau.txt.meta.json _i`.
- Job pesanti (CET, da cpu_busy_policy.log): τ 14:50:59–14:52:37; div code/chat 14:52:37–14:54:58; div edit_np 14:54:58–14:56:29; tauhist 14:57:13–14:57:29.

## Limiti
- Il verdetto "nessun bug trovato" dipende dalle forme (iv)/(v), aggiunte dopo il PREREG (prima di vedere i risultati T2, ma dopo aver visto i margini loggati nelle tracce); per la lettera del PREREG il verdetto è `bug`.
- (iv)/(v) dimostrano che la run è deterministica e che A1/B1 hanno scelto l'argmax del target nel loro stato reale; non dimostrano formalmente che il rollback dello stato
  ricorrente (`seq_rm` parziale, use_ckpt_tgt=false) sia esatto. Indizio contrario a un errore: (i) vs (iv) su prompt non divergenti max 0.5456 ≤ τ (forma senza rollback).
  Un test diretto (stato dopo rollback vs stato ricostruito da zero con la stessa storia di soli token accettati) non è stato fatto.
- τ è stimato su 5 prompt code (i primi 5 idonei in ordine di file erano tutti HumanEval): nessun prompt chat nel campione di τ.
- Proxy CPU (Xeon AVX-512/AMX, 8 vCPU): nulla si trasferisce automaticamente a Strata/AMD.
- PID 743382 (build ROCm) non era più presente in `ps` all'inizio del lavoro; nulla della build né di logs/rocm644_v2 è stato toccato. Durante i job girava in parallelo una run Bench (diag_greedy_aprime, nice 19, -t 6): non influisce sui numeri (deterministici), solo sui tempi.
