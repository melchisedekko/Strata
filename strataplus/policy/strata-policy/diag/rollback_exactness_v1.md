# Esattezza del rollback dello stato ricorrente: verifica v1 (PREREG v2, Parte B), code/chat
Proxy CPU, non AMD. llama.cpp d327bf1 con modifiche locali, build /workspace/llama.cpp/build-nollamafile. GGUF qwen35-2b-mtp-q4_k_m (sha256 18c92228…4f0b). Scritto il 2026-10-27 CET.
I dati per edit sono solo aggregati, in rollback_exactness_v1_edit_np.md.

## Verdetto (PREREG v2 + addenda 1-3)
- **code/chat: ESATTO.** 261/261 round validi (100% ≥ 80%). N1=0, N2=0, E1/E2/E3 soddisfatti.
- **edit_np: ESATTO** (113/113 validi, vedi il file _edit_np).
- **Globale: ESATTO.**
- In tutti i 374 round testati (accepted < k_proposed), il rollback via seq_rm è bit-esatto, nello stato e nei logit:
  - (a) storia reale con seq_rm;
  - (d) stessa storia con i token rifiutati sostituiti (t XOR 1) e poi lo stesso seq_rm;
  - (a) e (d) sono **bit-identici** su stato KV, conv e ricorrente e su tutte le righe Q dei logit.
- Quindi i token rifiutati non lasciano traccia dopo il rollback, e non c'è file:line da segnalare.
- Le differenze fra (a), (b) e (c) sono diverse forme di batch su CPU, non perdita di stato:
  - (b) senza seq_rm, con i soli token committati negli stessi round;
  - (c) prefill da zero.
  - Nessuno scambio di top-1 ha un margine di riferimento > τ, e |Δl1| ≤ τ sempre.
- Il controllo descrittivo GGML_CPU_TILED_MM=0 previsto dall'Addendum 1 **non è stato eseguito**: è rinviato per budget e per non sovrapporsi al processo di Bench.
  - Il PREREG non lo usa per il verdetto (Addendum 1: solo descrittivo), quindi il verdetto non dipende da quel controllo.
  - La parte "attribuzione delle differenze (a)-(b) al matmul tiled" resta **non determinata, rinviata**.

Preregistrazione (in /workspace/policy-local/arbiter_diag/, non modificati):

| file | sha256 |
|---|---|
| PREREG_v2.md | 72cac4362b54905f4ada4f9b1781eb8ebdb8fb114da3e65689bb3b13a07163a3 |
| PREREG_v2_addendum1.md (strato T<8/≥8, controllo tiled) | a92e515d89fa34a811aa5212f6d90c216a9c01de692a1b107001ba29d9baa7e7 |
| PREREG_v2_addendum2.md (verdetto letterale v1 = 'bug') | 2640c1bd750d57af385544b9f2c3fbc2ddc332caaf607cb27482767263d10adc |
| PREREG_v2_addendum3.md (ritira l'attribuzione al GDN; candidato FA) | 41622daa543f520b142fd832344eeef87aa86ac6fe7aa40c94e5363b5ff302dc |

Nessuna differenza è attribuita al GDN.

## Rumore di fondo (code/chat)
- F_log = 0 e F_state = 0: (a) vs (a') e (c) vs (c') sono bit-identici in 261/261 round, su stato e logit.
- Ogni soglia "≤ floor" è quindi uguaglianza bit per bit.
- τ = 0.566763 (dal v1).

## Validità
- (a) riproduce i vmargin loggati del round r+1 in 261/261 casi (stesso top-1, |Δgap| ≤ 1e-5).
- Ogni seq_rm ha restituito true (0 job con seq_rm=false).

## Numeri aggregati code/chat (riga 0 = posizione successiva, vocabolario completo 248320)

| confronto | round | stato bit-identico | logit (tutte le righe Q) bit-identici | max\|Δ\| riga0 max / p99 / mediana | max\|Δl1\| riga0 | flip top-1 (margine rif.) | flip con margine > τ |
|---|---|---|---|---|---|---|---|
| (a)-(a') | 261 | 261 | 261 | 0 / 0 / 0 | 0 | 0 | 0 |
| (c)-(c') | 261 | 261 | 261 | 0 / 0 / 0 | 0 | 0 | 0 |
| (a)-(d) | 261 | 261 | 261 | 0 / 0 / 0 | 0 | 0 | 0 |
| (a)-(b) | 261 | 237 | 237 | 0.725916 / 0.664635 / 0 | 0.377709 | 0 | 0 |
| (a)-(c) | 261 | 0 | 0 | 1.584323 / 1.133610 / 0.672990 | 0.514604 | 7 (0.002607, 0.002974, 0.035549, 0.037636, 0.078398, 0.264616, 0.264618) | 0 |

Max|Δ| delle sezioni di stato (unità del tipo: KV f16, conv/ricorrente f32):
- (a)-(b), 24 round diversi: kv_k 0.402, kv_v 0.637, conv 0.521, rec 0.0818.
- (a)-(c), 261 round diversi: kv_k 2.240, kv_v 1.246, conv 1.628, rec 0.166.

Per braccio:
- A1: 184 round.
  - (a)-(d): 184/184 bit.
  - (a)-(b): 167/184 stato bit, max|Δ| riga0 0.703148, max|Δl1| 0.377709.
  - (a)-(c): 0/184, max|Δ| 1.584323, max|Δl1| 0.514604, 6 flip (margini ≤ 0.264618).
- B1: 77 round.
  - (a)-(d): 77/77 bit.
  - (a)-(b): 70/77, max|Δ| riga0 0.725916, max|Δl1| 0.377709.
  - (a)-(c): 0/77, max|Δ| 1.283534, max|Δl1| 0.486025, 1 flip (margine 0.002974).

Stratificazione descrittiva (T_r = righe del batch del round r; T_q = righe di Q):

| strato | round | (a)-(d) bit | (a)-(b) stato bit | (a)-(b) max\|Δ\| riga0 | (a)-(c) max\|Δ\| riga0 | flip (a)-(c) |
|---|---|---|---|---|---|---|
| T_r < 8 | 252 | 252 | 237 | 0.725916 | 1.584323 | 7 |
| T_r ≥ 8 | 9 | 9 | **0** | 0.703148 | 0.945948 | 0 |
| T_q = 1 | 12 | 12 | 11 | 0.536984 | 0.819469 | 1 |
| T_q ≥ 2 | 249 | 249 | 226 | 0.725916 | 1.584323 | 6 |

Lettura per T_r:
- Con T_r ≥ 8, (a) e (b) differiscono sempre (9/9). Questo è coerente con l'ipotesi del matmul tiled per ≥ 8 righe (tiled.cpp L1202-1205), ma non è verificato: il controllo TILED_MM=0 è rinviato.
- Con T_r < 8 ci sono 15 differenze (a)-(b) non spiegate da quell'ipotesi; non sono attribuite.

## Per prompt (code/chat)
Colonne: round testati/validi; (a)≡(d) come stato+logit bit-identici; numero di round con (a)-(b) e (a)-(c) bit-identici; max|Δ| riga 0; max|Δl1|; flip di top-1 (nessuno con margine di riferimento > τ).

| prompt | braccio | round testati/validi | (a)≡(d) stato+logit bit | (a)≡(b) stato bit | (a)≡(c) stato bit | max\|Δ\| riga0 (a)-(b) | max\|Δ\| riga0 (a)-(c) | max\|Δl1\| (a)-(b) | max\|Δl1\| (a)-(c) | flip top-1 (b)/(c) |
|---|---|---|---|---|---|---|---|---|---|---|
| HumanEval/13 | A1 | 10/10 | 10+10 | 8 | 0 | 0.558098 | 1.124547 | 0.099866 | 0.492290 | 0/0 |
| HumanEval/13 | B1 | 7/7 | 7+7 | 7 | 0 | 0.000000 | 1.283534 | 0.000000 | 0.486025 | 0/0 |
| HumanEval/35 | A1 | 4/4 | 4+4 | 4 | 0 | 0.000000 | 0.627023 | 0.000000 | 0.080021 | 0/1 |
| HumanEval/35 | B1 | 1/1 | 1+1 | 1 | 0 | 0.000000 | 0.592824 | 0.000000 | 0.070805 | 0/0 |
| HumanEval/55 | A1 | 3/3 | 3+3 | 3 | 0 | 0.000000 | 1.085807 | 0.000000 | 0.422411 | 0/0 |
| HumanEval/55 | B1 | 2/2 | 2+2 | 2 | 0 | 0.000000 | 1.023792 | 0.000000 | 0.245442 | 0/0 |
| HumanEval/59 | A1 | 14/14 | 14+14 | 13 | 0 | 0.574026 | 1.584323 | 0.089706 | 0.514604 | 0/1 |
| HumanEval/59 | B1 | 9/9 | 9+9 | 9 | 0 | 0.000000 | 1.118832 | 0.000000 | 0.269930 | 0/0 |
| HumanEval/91 | A1 | 4/4 | 4+4 | 3 | 0 | 0.703148 | 0.835732 | 0.187117 | 0.305085 | 0/0 |
| HumanEval/91 | B1 | 2/2 | 2+2 | 1 | 0 | 0.536984 | 0.656013 | 0.031513 | 0.098240 | 0/0 |
| HumanEval/101 | A1 | 2/2 | 2+2 | 1 | 0 | 0.558033 | 0.705461 | 0.104428 | 0.021441 | 0/0 |
| HumanEval/101 | B1 | 1/1 | 1+1 | 0 | 0 | 0.725916 | 0.835879 | 0.065228 | 0.073986 | 0/0 |
| HumanEval/148 | A1 | 1/1 | 1+1 | 0 | 0 | 0.601738 | 0.693684 | 0.073925 | 0.165930 | 0/0 |
| HumanEval/148 | B1 | 0 | – | – | – | – | – | – | – | – |
| mtbench-101 | A1 | 29/29 | 29+29 | 28 | 0 | 0.664635 | 0.887563 | 0.004124 | 0.293240 | 0/1 |
| mtbench-101 | B1 | 9/9 | 9+9 | 9 | 0 | 0.000000 | 0.923560 | 0.000000 | 0.314779 | 0/0 |
| mtbench-105 | A1 | 23/23 | 23+23 | 21 | 0 | 0.544317 | 0.991290 | 0.140245 | 0.317946 | 0/1 |
| mtbench-105 | B1 | 5/5 | 5+5 | 4 | 0 | 0.544317 | 0.832150 | 0.140245 | 0.178850 | 0/0 |
| mtbench-115 | A1 | 33/33 | 33+33 | 32 | 0 | 0.586701 | 0.981290 | 0.042589 | 0.322292 | 0/0 |
| mtbench-115 | B1 | 12/12 | 12+12 | 12 | 0 | 0.000000 | 0.891242 | 0.000000 | 0.213398 | 0/0 |
| mtbench-121 | A1 | 19/19 | 19+19 | 18 | 0 | 0.561972 | 0.965338 | 0.062954 | 0.317495 | 0/1 |
| mtbench-121 | B1 | 8/8 | 8+8 | 8 | 0 | 0.000000 | 0.839550 | 0.000000 | 0.116009 | 0/0 |
| mtbench-129 | A1 | 32/32 | 32+32 | 31 | 0 | 0.512393 | 1.133610 | 0.117683 | 0.374886 | 0/1 |
| mtbench-129 | B1 | 13/13 | 13+13 | 13 | 0 | 0.000000 | 0.984509 | 0.000000 | 0.330002 | 0/1 |
| mtbench-136 | A1 | 10/10 | 10+10 | 5 | 0 | 0.658395 | 0.817590 | 0.377709 | 0.111804 | 0/0 |
| mtbench-136 | B1 | 8/8 | 8+8 | 4 | 0 | 0.618084 | 0.899416 | 0.377709 | 0.280653 | 0/0 |

HumanEval/148 B1 non ha round con accepted < k_proposed.

## Comandi (cwd /workspace/strata-bench, P=/workspace/policy-local/arbiter_diag, D=traces v3 in sola lettura)
```
L=/workspace/llama.cpp; B=$L/build-nollamafile
c++ -std=c++17 -O3 -DNDEBUG -DGGML_BACKEND_SHARED -DGGML_SHARED -DGGML_USE_CPU -DLLAMA_SHARED -I$L/common -I$L/vendor -I$L/include -I$L/ggml/include \
  /workspace/strata-policy/diag/rollback_probe.cpp -L$B/bin -lllama-common -lllama -lggml -lggml-base -Wl,-rpath,$B/bin -o $P/rollback_probe
python3 /workspace/strata-policy/diag/make_rollback_jobs.py $P/div_codechat.json $D/aprime_r1.jsonl $D/default_a_r1.jsonl $P/jobs_rb_codechat.txt
$P/run_rollback.sh "" codechat edit_np      # = per ogni set:
nice -n 10 $P/rollback_probe -m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 \
  -c 8192 -b 8192 -ub 512 --no-repack --spec-draft-n-max 3 --dmax 7 --jobs $P/jobs_rb_codechat.txt --out $P/rb_codechat.jsonl
python3 /workspace/strata-policy/diag/rollback_analyze.py $P/rb_codechat.jsonl $P/jobs_rb_codechat.txt.meta.json $P/rb_codechat_analysis.json
```
- `-t 6` come nella run v3, per riprodurre la forma numerica; GGML_CPU_TILED_MM non impostato (default: tiled attivo).
- Finestre: code/chat 15:15:51-15:49:59 CET; il secondo set 15:49:59-16:11:38 CET (START/END in cpu_busy_policy.log).

## sha256

| file | sha256 |
|---|---|
| rollback_probe.cpp | 59e8824f5112b77a03f59a6da10b078ab4ae68902313cecaa78378d060c85320 |
| make_rollback_jobs.py | 3cf98f9cde9f74a8a3348cbe8a098c75cd2582b2ed719b9c2dcd9943eb9a9f5b |
| rollback_analyze.py | 746062b8825cf3261196ea9f7b07a003e32f44e6d5ec7a7c9b8c5efc7da46d83 |
| binario rollback_probe | c6cea8aa9399f7c40e3e9b6cdb10bd9bd40c0ab0c16e95cd6064d7c857ee71f8 |
| run_rollback.sh | 8d30c0f04143a06cbb517524f2c03232aa339e5ea7c060fbb3d51752d2dec6fa |
| jobs_rb_codechat.txt | 083fab22495b7bfe1fecddb0f37c2cdc9293530471987b39d9179512c1944956 |
| rb_codechat.jsonl | 609f9a87105f288a8816f7c0e81bd1487e0a247cbbec32f8ff47b820e47b7ce2 |
| rb_codechat_analysis.json | 63d08976279f264497dce3809ee19f451b4cecd972e1a511b704543258657ee8 |

## Limiti
- **Sovrapposizione di processi llama.** rollback_probe (PID 786856, START 15:15:51 CET) si è sovrapposto alla run aprime_tm0 di Bench (PID 780678, attiva dalle 15:12:38 CET). Questo viola la regola "un solo processo llama alla volta".
  - I confronti greedy e bit per bit restano validi: sono deterministici e non dipendono dai tempi.
  - **Nessun tempo di questa finestra va usato.**
  - Anche il secondo set (fino alle 16:11:38 CET) gira nella stessa finestra.
- **Controllo GGML_CPU_TILED_MM=0 non eseguito** (rinviato per budget e per la sovrapposizione con Bench). L'attribuzione delle differenze (a)-(b) e (a)-(c) a matmul tiled o a flash attention resta non determinata, rinviata. Il verdetto PREREG v2 non ne dipende.
- **FA nella run v3:** attiva per deduzione dal codice, non dal log (Addendum 3).
  - flash_attn_type AUTO con solo CPU (llama-context.cpp L322-323, L659-661).
  - Coerente: lo stato KV serializzato ha v_trans=0.
- **Copertura dei round:** si testano solo i round con accepted < k_proposed dei 20 prompt divergenti, fino alla divergenza registrata. Il test non copre i round accettati per intero né i prompt non divergenti.
- **Cosa "ESATTO" esclude e cosa no:**
  - Esclude che il rollback lasci stato residuo dei token rifiutati (in questa configurazione: n_rs_seq=7, -ub 512, CPU, -t 6).
  - Non spiega da sola le divergenze A1/B1. Quelle restano coerenti con differenze di forma del batch (vedi (a)-(b), (a)-(c)) e quasi-pareggi FP. Il verdetto letterale PREREG v1 era 'bug' (Addendum 2).
- **Incidenti di processo:**
  - Un primo lancio (15:14:17-15:15:16 CET) è stato interrotto per un errore del parser dello stato (header magic+seq_id di 8 byte non saltato); dati scartati.
  - Due test di sviluppo del parser di pochi secondi verso le 15:15 CET.
  - Tutto è registrato in cpu_busy_policy.log.
