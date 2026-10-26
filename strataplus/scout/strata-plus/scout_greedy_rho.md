# Scout: greedy identity nella verifica speculativa (CPU, llama.cpp) e ρ_mtp su Qwen3.5-2B

Data: 25/10/2026 (ora di Roma). Codice llama.cpp citato al commit `d327bf1f0780f87b8c01b367b61853b0c291d7c4` (master del 24/10/2026, 22:54 ora di Roma).
Base dei permalink: `https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/`. Tutti i link qui sotto sono stati aperti e verificati in questa sessione.
Legenda: **[IMPL]** = implementato/merged · **[PROP]** = proposto (PR aperta o chiusa senza merge, branch fuori upstream) · **[NON TROVATO]** · **[ANALISI]** = mia lettura del codice, non riportata da nessuno.

---

## Domanda 1: articoli su batch invariance e non-determinismo legato alla forma del batch

- **Thinking Machines, "Defeating Nondeterminism in LLM Inference"**. Il post esiste.
  - URL: https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
  - Autore: Horace He. Data: 10/09/2025. DOI 10.64434/tml.20250910.
  - Tesi: il singolo forward pass è deterministico run-to-run. Ciò che manca è la *batch invariance*: il risultato di una riga dipende da quante righe ci sono nel batch.
  - Cause indicate: split-K e scelta della strategia o dell'istruzione in base alla forma, split-KV in attention (FlashDecoding), KV-cache gestita in modo diverso dai token correnti.
  - Dice esplicitamente che il problema riguarda anche gli endpoint su CPU.
  - Fix proposti: configurazione dei kernel fissa indipendentemente da M, split-size fissa sul KV, aggiornare la KV-cache prima dell'attention.
  - Numeri: Qwen3-235B, su 1000 completamenti 80 risultano unici, che diventano 1000 identici con i kernel invarianti. Tempi: 26 s di default, 55 s deterministico non ottimizzato, 42 s con attention migliorata.
  - Il caso Strata (T=1 contro T>1 sulla stessa sequenza) è proprio la batch-shape invariance lungo la dimensione token.
- **LMSYS / SGLang, "Towards Deterministic Inference in SGLang and Reproducible RL Training"** (22/09/2025): https://www.lmsys.org/blog/2025-09-22-sglang-deterministic/
- **Doc SGLang "Deterministic Inference"**: https://docs.sglang.io/docs/advanced_features/deterministic_inference
- **Doc vLLM "Batch Invariance"** (beta): https://docs.vllm.ai/en/latest/features/batch_invariance/
- **Nota**: la frase di ggerganov in llama.cpp è la sintesi più chiara: *"This is expected - we use different kernels for different batch sizes."* Link: https://github.com/ggml-org/llama.cpp/issues/23335#issuecomment-4488338528 (19/05/2026).

## Domanda 2: llama.cpp, decode speculativa ≠ decode normale

### Issue, PR e discussioni (verificate con `gh`)

| # | Stato | Cosa dice |
|---|---|---|
| [#23335](https://github.com/ggml-org/llama.cpp/issues/23335) | chiusa | "draft-mtp changes deterministic output on Qwen3.6 MTP model". Metal, Q4_K_M. Il comportamento è atteso: kernel diversi per batch size diversi ([commento ggerganov](https://github.com/ggml-org/llama.cpp/issues/23335#issuecomment-4488338528)). am17an: tenere la FA in F32 "*may* approximate batch-invariant behavior" ([commento](https://github.com/ggml-org/llama.cpp/issues/23335#issuecomment-4489342548)). Con Q8_0 l'utente non riproduce più la divergenza ([commento](https://github.com/ggml-org/llama.cpp/issues/23335#issuecomment-4489296518)). |
| [#25618](https://github.com/ggml-org/llama.cpp/issues/25618) | **aperta** | "Speculative decoding (draft-mtp / draft-dspark): greedy output diverges from vanilla on quantized targets". Repro su Vulkan, Metal, ROCm, CUDA e SYCL. Root cause per backend: su Vulkan GQA packing nella FA, split_k, p021 contro GEMM, mul_mat_vec Q8_0 a N=1 contro quantize_q8_1+MMVQ a N=2; su Metal mul_mv contro mul_mv_ext e nsg della FA; su CUDA dispatch mmvq/MMVF e FA. Un commento riporta che in quel replay specifico "CPU row 0 was also exact". |
| [#27407](https://github.com/ggml-org/llama.cpp/issues/27407) | chiusa per inattività (09/10/2026, NOT_PLANNED) | CUDA: greedy diverge con verifica batched, divergenza deterministica. Apoze individua MMVF e i path FA dipendenti dalla larghezza. Il suo fix porta parità per n_max 1..3, ma non per n_max ≥4. |
| [#28111](https://github.com/ggml-org/llama.cpp/issues/28111) | aperta | CUDA SM120: mul_mat non batch-invariant per le quant IQ a n=5 e n=8. Propone un test MUL_MAT_BATCH_INVARIANCE. |
| [#16016](https://github.com/ggml-org/llama.cpp/pull/16016) | **[PROP]** aperta, mai mergiata | "Deterministic inference mode (CUDA)": `-DGGML_DETERMINISTIC=ON` / `--deterministic`, solo CUDA BF16/FP16. JohannesGaessler: *"I don't want to maintain guarantees for bit-for-bit identical results as the batch size is varied."* ([discussione](https://github.com/ggml-org/llama.cpp/pull/16016)) |
| [#26358](https://github.com/ggml-org/llama.cpp/pull/26358) | **[PROP]** chiusa senza merge | Vulkan: disabilita il GQA packing nella FA per query multi-token. |
| [#28108](https://github.com/ggml-org/llama.cpp/pull/28108) | **[PROP]** chiusa senza merge | CUDA: FA batch-invariant per larghezze strette su SM120. Aggiunge test_flash_attn_ext_batch_invariance. Chiusa per la policy sull'uso di AI. |
| [#28109](https://github.com/ggml-org/llama.cpp/pull/28109) | **[PROP]** aperta | Test di batch invariance per GATED_DELTA_NET: n token in una chiamata contro n chiamate da 1 token, con memcmp. Verificato solo su CUDA. |
| [#28488](https://github.com/ggml-org/llama.cpp/pull/28488) | **[PROP]** aperta (draft) | "Spec dec bug tests" per #25618. **Dichiara "CPU 23/23 OK"**, contro 12/23 su Vulkan. Attenzione: sono test di singoli op in test-backend-ops, che non passano dal buffer *repack* né dal path *tiled* usati dal modello reale (vedi sotto). |
| [#27441](https://github.com/ggml-org/llama.cpp/pull/27441) | **[PROP]** aperta | Metal: split-K deterministico a ordine fisso per batch piccoli. Riproducibile run-to-run, ma cambia ancora i "greedy ties" rispetto ai kernel stock. |
| [#27694](https://github.com/ggml-org/llama.cpp/pull/27694) | **[IMPL]** merged il 02/10/2026 | Drafter probabilistico e verifica per rejection sampling (simple draft e MTP). Non risolve la bit-identity. |
| Branch Apoze | **[PROP]** fuori upstream | https://github.com/Apoze/llama.cpp/commit/6263445513416ef93fd5d05391299f33c64702fa (CUDA, fix/cuda-speculative-batch-invariance) |

**[NON TROVATO]**: nessuna issue o PR di llama.cpp che riporti la divergenza spec/vanilla **su backend CPU**. Le ricerche "speculative CPU greedy", "MTP CPU output differs", "batch invariant CPU" e "repack gemm gemv" non hanno dato risultati. Il caso Strata (CPU, Qwen3.5-2B-MTP Q4_K_M) sarebbe quindi un caso nuovo da segnalare.

### [ANALISI] Dove ggml-cpu cambia path di calcolo in base a T (n_tokens = ne11)

Questa è la mia lettura del codice: è un'ipotesi da confermare sperimentalmente.

1. **Repack Q4_K (x86 AVX2, attivo di default)**
   - I pesi Q4_K vengono riscritti come `q4_K_8x8_q8_K` ([repack.cpp L5011-5015](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/repack.cpp#L5011-L5015)).
   - Nel mul_mat: *"If there are more than three rows in src1, use gemm; otherwise, use gemv"* ([repack.cpp L4637-4648](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/repack.cpp#L4637-L4648)).
   - Le attivazioni vengono quantizzate a blocchi di 4 righe (`quantize_mat` 4x8) e le righe residue con `from_float` ([repack.cpp L4697-4707](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/repack.cpp#L4697-L4707)).
   - Conseguenza: T≤3 e T≥4 usano kernel diversi. Il token j di un batch T=5 passa da gemm o gemv a seconda della sua posizione. È la candidata n.1 per la tua divergenza (Q4_K_M ha la maggior parte dei pesi in Q4_K).
2. **Tiled K-quant matmul (default ON)**
   - Si attiva per Q2_K…Q6_K e IQ* non repackati quando ne11 ≥ 8 ([tiled.cpp L1202-1223](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/tiled/tiled.cpp#L1202-L1223)).
   - Si disattiva con l'env `GGML_CPU_TILED_MM` ([tiled.cpp L573-592](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/tiled/tiled.cpp#L573-L592)).
   - Riguarda i tensori Q6_K o Q5_K (su x86 non vengono repackati), tra cui l'`output`/`token_embd`, se è Q6_K.
3. **llamafile sgemm**
   - Si attiva solo con n ≥ 2: *"only enable sgemm for prompt processing"* ([sgemm.cpp L3909-3913](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/llamafile/sgemm.cpp#L3909-L3913)).
   - Chiamata in [ggml-cpu.c L1301-1326](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/ggml-cpu.c#L1301-L1326) e [L1386-1408](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/ggml-cpu.c#L1386-L1408).
   - Riguarda solo i tensori F32, F16, BF16, Q8_0, Q4_0 e simili (non i K-quant), quindi eventuali tensori F32/F16 piccoli.
4. **ARM i8mm**
   - Q4_K e Q6_K hanno `.nrows = 2` sotto `__ARM_FEATURE_MATMUL_INT8` ([ggml-cpu.c L311-336](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/ggml-cpu.c#L311-L336)).
   - Il vec_dot a 2 righe si usa solo se ne11 è pari ([L1456-1463](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/ggml-cpu.c#L1456-L1463)). Vale solo su ARM.
5. **Flash attention**
   - Il path split-KV si usa solo con `neq1 == 1` e KV ≥ 512, cioè nella decode e non nella verifica ([ops.cpp L9585](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/ops.cpp#L9585)).
   - FA tiled con Q ≥ GGML_FA_TILE_Q=64 ([ops.cpp L9642-9653](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/ops.cpp#L9642-L9653)).
   - Conseguenza: oltre 512 token di contesto, T=1 e T>1 riducono il softmax in ordine diverso. Nel modello ci sono 6 layer di full attention su 24.
6. **Gated DeltaNet**
   - Il grafo sceglie autoregressive o fused per T=1 e chunked o fused per T>1 ([delta-net-base.cpp L422-445](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/src/models/delta-net-base.cpp#L422-L445)).
   - Il kernel CPU fused cicla per token ([ops.cpp L11219-11372](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/ops.cpp#L11219-L11372)), quindi è probabilmente invariante quando il fused è attivo. Se il fused è disattivo, il chunked non lo è.
7. **Chunking dei thread** ([ggml-cpu.c L1417-1437](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/src/ggml-cpu/ggml-cpu.c#L1417-L1437)): cambia solo la partizione del lavoro, non l'ordine di riduzione per elemento. Non è un colpevole.

**Esperimenti suggeriti (ablation, uno alla volta, misurando identity/90):**
- `-nr` / `--no-repack` ([arg.cpp L2434-2438](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/arg.cpp#L2434-L2438))
- `GGML_CPU_TILED_MM=0`
- `-fa off`
- build con `-DGGML_LLAMAFILE=OFF`

Previsione **non verificata**: con i quattro insieme, su x86 si dovrebbe tornare vicini a 90/90. Il mul_mat_one_chunk con vec_dot riga per riga è invariante rispetto a T. Il costo è un prefill/verify più lento.

## Domanda 3: soluzioni esistenti (kernel batch-invariant)

- **[IMPL]** Thinking Machines `batch_invariant_ops` (PyTorch/Triton: mm, addmm, log_softmax, mean): https://github.com/thinking-machines-lab/batch_invariant_ops
- **[IMPL, beta]** vLLM, `VLLM_BATCH_INVARIANT=1`: https://docs.vllm.ai/en/latest/features/batch_invariance/
  - Hardware: NVIDIA ≥ sm80, AMD Instinct, Intel XPU. **Non CPU**.
  - Tracking: https://github.com/vllm-project/vllm/issues/27433 (aperta).
- **[IMPL]** SGLang ≥0.5.3, `--enable-deterministic-inference` (backend flashinfer, fa3 o triton; split-KV fisso; slowdown medio 34% secondo il blog): https://docs.sglang.io/docs/advanced_features/deterministic_inference. Solo GPU.
- **llama.cpp**:
  - **[NON TROVATO]** nessun flag di determinismo o batch-invariance in upstream (grep su `common/arg.cpp`, `llama-context`, server).
  - Esiste `ggml_backend_cpu_set_use_ref` ([ggml-cpu.h L24](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/ggml/include/ggml-cpu.h#L24)), ma è solo un'API interna usata dai test (tests/test-tiled-mulmat.cpp), senza flag CLI.
  - **[IMPL] solo indiretti**: `--no-repack` e `GGML_CPU_TILED_MM=0` esistono, ma non sono pensati per il determinismo.
  - **[PROP]**: #16016 (solo CUDA, posizione dei maintainer contraria a garanzie bit-exact), #26358, #28108, #28109, #28488, #27441, branch Apoze.
  - Linea ufficiale: per avere bit-identity si usa #27694 (rejection sampling) oppure si accetta la divergenza.

---

## Domanda 2bis: ρ_mtp e peso della lm_head (Qwen/Qwen3.5-2B)

Fonte: https://huggingface.co/Qwen/Qwen3.5-2B/blob/main/config.json. Conteggio parametri fatto da me sull'header del safetensors (sha HF `15852e8c16360a2fea060d615a32b45270f8a8fc`).

**Config:**
- hidden_size 2048, num_hidden_layers 24 (18 linear_attention + 6 full_attention), intermediate_size 6144.
- vocab_size 248320, tie_word_embeddings **true**.
- mtp_num_hidden_layers 1, mtp_use_dedicated_embeddings false.

**Parametri:**

| Componente | Parametri | Note |
|---|---|---|
| Totale | 2.274.069.824 | |
| embed / lm_head (tied) | **508.559.360** | 248320×2048 |
| Corpo testo | 1.373.265.728 | |
| Visione | 331.416.576 | |
| MTP | 60.828.160 | |

- Non esiste un tensore lm_head separato.
- **La lm_head pesa il 27,0% del modello testo** (corpo + embed = 1,882 G) e il 22,4% del totale con la visione.

**Stima del costo MTP** (MAC per token, attention/KV ignorati):
- passo MTP ≈ 60,8 M + 508,6 M = 569,4 M
- forward target ≈ 1.882 M
- **ρ ≈ 0,30**, coerente con il **0,258 misurato**. Senza lm_head il ρ sarebbe circa 0,032.
- In Q4_K_M l'`output`/embedding è tipicamente a precisione più alta (es. Q6_K) e pesa ancora di più in byte. Non l'ho verificato su quel GGUF specifico.

**La testa MTP di llama.cpp ricalcola la lm_head completa a ogni passo: sì.**
- In `graph_mtp` di Qwen3.5 si fa `head_w = layer.nextn.shared_head_head ? … : model.output; cur = build_lora_mm(head_w, cur, head_s);`. È la matrice [n_embd, n_vocab] intera, senza vocabolario ridotto: [qwen35.cpp L644-662](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/src/models/qwen35.cpp#L644-L662).
- `model.output` = `token_embd` quando l'embedding è tied: [L44-52](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/src/models/qwen35.cpp#L44-L52).
- Lm_head del target: [L233](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/src/models/qwen35.cpp#L233).

**Confronto con il ~0,059 stimato da Strata per la MoE:**
- Il motore Strata usa un *draft vocabulary* ridotto ([src/core/mtp.cpp](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/core/mtp.cpp), `dvocab_`/`dhead_`; file `data/draft_vocab*.bin`). llama.cpp non lo fa.
- Dimensioni dei file (lette sul box): default 106.299 token, cyrillic 58.963, fr 46.211, en 40.525.
- Sul 2B, con la stessa stima, il ρ diventerebbe circa 0,148 (default), 0,096 (cyrillic) o 0,076 (en).
- Conclusione: il 0,258 misurato con llama.cpp **non è confrontabile** con lo 0,059 di Strata finché la lm_head è completa (248k).
- **[NON TROVATO / non verificato]**: non ho controllato la config di Qwen3.8-Flash-Next né la formula esatta di Strata che produce 0,059.
- Nota qualitativa: in una MoE il forward target conta solo i parametri *attivi*, quindi una lm_head completa peserebbe in proporzione **di più**, non di meno. Uno 0,059 è plausibile solo con vocabolario ridotto o con un denominatore che include molti parametri attivi.

---

## Ipotesi dopo esclusione repack (follow-up 25/10/2026)

**Contesto (riferito da Strata Bench, non verificato da me):** tutti i run usavano già `--no-repack`. La divergenza resta anche con verifica a T=2, mentre con verifica forzata a T=1 si ha 30/30. Il candidato n.1 indicato sopra (repack Q4_K) va quindi **scartato**.

**Codice esaminato:** llama.cpp commit `d327bf1f0780f87b8c01b367b61853b0c291d7c4`. Il 25/10/2026 era ancora la punta di `master` (fetch rifatto). Base permalink: `B = https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/`

**GGUF esaminato:** `unsloth/Qwen3.5-2B-MTP-GGUF`, file `Qwen3.5-2B-Q4_K_M.gguf`, revisione HF `e05864f8066d874d5f85aaff007ae57a2a7d1efe`. Ho letto solo l'header (primi 25 MB via HTTP range):
https://huggingface.co/unsloth/Qwen3.5-2B-MTP-GGUF/blob/e05864f8066d874d5f85aaff007ae57a2a7d1efe/Qwen3.5-2B-Q4_K_M.gguf

⚠️ Non so se Strata Bench usi esattamente questo file: va confermato sul GGUF reale, ad esempio con `gguf-dump`.

### Verificato nel codice

**V1. Gated DeltaNet: stesso op e stesso kernel per T=1 e T>1. Non c'è uno scan chunked/parallelo nel percorso di default.**
- `build_delta_net` sceglie tra due percorsi:
  - se `n_seq_tokens == 1`, usa il fused se `fused_gdn_ar`, altrimenti l'autoregressivo;
  - se T>1, usa il fused se `fused_gdn_ch`, altrimenti `build_delta_net_chunking` (questo è il percorso chunked vero e proprio).
  - Righe: B + `src/models/delta-net-base.cpp#L422-L445`
- Entrambi i flag sono forzati a `true`, con `auto_fgdn = false`. Rif: B + `src/llama-context.cpp#L325-L327`.
  - Le probe a L132-142 e la risoluzione a L664-668 vengono usate solo se `auto_fgdn`.
  - In `common/`, `include/` e `tools/` non c'è nessun flag CLI che li cambi (grep).
- Il percorso fused chiama `ggml_gated_delta_net(..., K=1)` per qualsiasi T: B + `src/models/delta-net-base.cpp#L370-L420`.
- Con snapshot di rollback (`n_rs_seq > 0`), si chiama lo stesso op con `K = n_rs_seq+1`: B + `src/models/delta-net-base.cpp#L524-L600`.
- Kernel CPU: B + `ggml/src/ggml-cpu/ops.cpp#L11219-L11370`.
  - Per ogni (head, seq) c'è un loop **sequenziale** `for t < n_tokens` (L11315) con le stesse operazioni F32 per ogni token: decay `exp(g)`, `vec_dot_f32` delta, `vec_mad` outer product, `vec_dot` output (L11326-L11356).
  - K>1 aggiunge solo `memcpy` degli snapshot (L11360-L11367).
  - Il parallelismo è solo su head×seq (L11373-L11412).
  - ⇒ Il risultato del token t non dipende da T.
- Lo stato ricorrente è in F32 (`recurrent_type_r/s = GGML_TYPE_F32`, B + `src/llama-model.cpp#L2931-L2932`), quindi il round-trip è lossless.
- `ssm_conv` è anch'esso un loop scalare per token e per riga: B + `ggml/src/ggml-cpu/ops.cpp#L10027-L10078`.

**V2. Matmul Q4_K/Q5_K/Q6_K con `--no-repack` su x86: stesso percorso a n=1 e n=2.**
- In `ggml_compute_forward_mul_mat` (B + `ggml/src/ggml-cpu/ggml-cpu.c#L1255-L1472`):
  - Il primo tentativo `llamafile_sgemm` (L1301-L1326) e il secondo, dopo la conversione dell'attivazione in `vec_dot_type` (L1328-L1377, Q8_K per le K-quant; L1386-L1408), falliscono.
  - Motivo: `llamafile_sgemm` non ha casi Q4_K/Q5_K/Q6_K e cade in `default: return false` (B + `ggml/src/ggml-cpu/llamafile/sgemm.cpp#L3896-L4240`).
- Ne segue:
  - quantizzazione Q8_K per riga di src1, indipendente da quante righe ci sono;
  - `vec_dot` per riga in `mul_mat_one_chunk` (L1166-L1253).
- Il percorso tiled richiede ≥8 righe di src1 (B + `ggml/src/ggml-cpu/tiled/tiled.cpp#L1202-L1223`), quindi è irrilevante a T=2.
- **Eccezione ARM:** con `__ARM_FEATURE_MATMUL_INT8`, `num_rows_per_vec_dot = 2` quando ne11 è pari (B + `ggml/src/ggml-cpu/ggml-cpu.c#L311-L336` e `#L1456-L1463`). Su ARM con i8mm, quindi, T=2 cambia kernel anche per le K-quant.

**V3. (Nuovo, candidato forte) Nel GGUF Q4_K_M esaminato `ssm_alpha.weight` e `ssm_beta.weight` sono F32 [2048×16] in tutti i 18 layer GDN (36 tensori). Con n≥2 passano da tinyBLAS, con n=1 da `ggml_vec_dot_f32`.**
- **Tipi letti dall'header del GGUF sopra:**
  - 36 tensori `ssm_(alpha|beta).weight` in F32;
  - conteggio complessivo: F32 176, Q4_K 113, Q6_K 27, Q5_K 18, Q8_0 1 (`blk.24.nextn.eh_proj`);
  - `output.weight` assente, quindi `token_embd` Q6_K è tied (per V2 resta invariante).
- **Uso nel grafo:** `build_lora_mm(ssm_beta, cur)` e `build_lora_mm(ssm_alpha, cur)` producono `beta` e `alpha`, cioè gate e decay del delta rule. Rif: B + `src/models/qwen35.cpp#L370-L380`.
- **Il percorso tinyBLAS è attivo:**
  - `GGML_LLAMAFILE` è ON di default nella build di llama.cpp (B + `CMakeLists.txt#L166-L167`).
  - Il guard `if (n < 2) return false` (non-MMA) è a B + `ggml/src/ggml-cpu/llamafile/sgemm.cpp#L3896-L3913`.
  - Il caso F32 è a L3920; su AVX/AVX2/AVX512 non c'è un'ulteriore soglia su n (su NEON serve n≥4).
  - In `tinyBLAS::matmul` con m=16 si arriva a `mnpack` per `m % 8 == 0` (B + `ggml/src/ggml-cpu/llamafile/sgemm.cpp#L568-L605`).
- **A n=1 ricade su `ggml_vec_dot_f32`** (B + `ggml/src/ggml-cpu/vec.cpp#L11-L135`). Su x86 accumula in `GGML_F32_ARR` registri interleaved e poi fa la riduzione. tinyBLAS accumula invece per tile lungo k con un altro ordine.
- **Ordine di somma diverso ⇒ risultato non bit-identico in generale.** La differenza entra in `alpha` (decay) e `beta` di ogni layer GDN e si propaga allo stato ricorrente.
- **Coerenza con i sintomi:** la divergenza è deterministica, assente a T=1 e presente a T=2. Questo è l'unico punto dei pesi del modello in cui T=1→T=2 cambia kernel su x86 con `--no-repack` e `-fa on`.
- Il collegamento al mismatch 51-60/90 **non è misurato**: vedi la sezione Plausibile.

**V4. Attention.**
- Con FA attiva c'è il percorso split-KV solo se `neq1 == 1` (T=1), K/V in F16/F32 e `nek1 >= 512`: B + `ggml/src/ggml-cpu/ops.cpp#L9584-L9586`.
  - ⇒ Con contesto ≥512 posizioni, T=1 e T=2 usano riduzioni softmax diverse nei 6 layer full-attention.
  - Il tiled FA richiede Q ≥ `ggml_fa_tile_config::Q` (L9642-L9653) e non riguarda T=2.
- Con `-fa off`, KQ e KQV sono `mul_mat` su KV cache F16. Su x86 con F16C, tinyBLAS F16 entra a n≥2 (sgemm.cpp L4048).

**V5. Strumenti per dumpare i tensori intermedi.**
- `examples/eval-callback` (binario `llama-eval-callback`) registra `params.cb_eval = common_debug_cb_eval` (B + `examples/eval-callback/eval-callback.cpp#L41-L57`).
  - Stampa op, shape, alcuni elementi e la `sum` di ogni tensore (B + `common/debug.cpp#L79-L186`).
  - È testo `%f`, quindi **non bit-esatto**.
- `examples/debug` (`llama-debug`) aggiunge `--tensor-filter REGEX` (B + `common/arg.cpp#L4624`), `--save-logits` e `--verbose` (B + `examples/debug/README.md`).
- Per un confronto bit-esatto: `llama_context_params.cb_eval` / `cb_eval_user_data` (B + `include/llama.h#L393-L394`), con callback propria in Strata Bench che scrive i byte grezzi.
- Nomi utili (`cb(...)` in `qwen35.cpp`), con suffisso `-<layer>`:
  - `beta`, `alpha`, `beta_sigmoid`, `a_softplus`, `gate`;
  - `conv_output_raw`, `q_conv_predelta`, `k_conv_predelta`, `v_conv_predelta`, `state_predelta`;
  - `linear_attn_out`, `attn_output`, `l_out`, `result_norm`, `result_output`.
- `GGML_SCHED_DEBUG` (B + `ggml/src/ggml-backend.cpp#L1962-L1963`) stampa split e assegnazione dei backend, **non i valori**. Non serve per trovare il layer.
- Come disattivare tinyBLAS, split-KV e tiled:
  - c'è un'API di backend, `ggml_backend_cpu_set_use_ref` (B + `ggml/include/ggml-cpu.h#L139`, controlli a `ggml-cpu.c#L1308`, `#L1387` e `ops.cpp#L9585`);
  - non c'è nessun flag CLI o env che la chiami: grep, l'unico uso è `tests/test-tiled-mulmat.cpp`.
  - In alternativa: build con `-DGGML_LLAMAFILE=OFF`.

### Plausibile (non misurato)
- **P1 (principale): V3 è la causa, o la causa dominante.**
  - Test decisivo: rebuild con `-DGGML_LLAMAFILE=OFF` (oppure `ggml_backend_cpu_set_use_ref(true)` nel backend CPU di Strata Bench), poi rifare il bench con verifica a T=2.
  - Atteso se P1 è vera: identità che sale verso 90/90, a contesto <512 o con `-fa on` e KV <512.
- **P2: il contributo di FA split-KV (V4)** dipende dalla lunghezza dei prompt e delle generazioni. Va separato ripetendo con contesto totale <512 oppure confrontando con `-fa off` (che però introduce tinyBLAS F16).
- **P3: MTP hidden state.** La PR aperta #30141 ("speculative : save and restore MTP hidden state") tocca solo la qualità del draft, non l'identità del target. Andrebbe esclusa solo se i test sopra non chiudono il gap.
- **P4: CPU ARM con i8mm.** La V2-eccezione aggiunge divergenza anche sulle K-quant. Va riportata l'architettura della macchina di Strata Bench.

### Non trovato
- Non ho trovato un percorso chunked/parallel-scan di GDN attivo di default su CPU: esiste (`build_delta_net_chunking`), ma è disattivato da `fused_gdn_ch = true`.
- Non ho trovato un flag CLI o env per disattivare llamafile/tinyBLAS o forzare `use_ref` a runtime.
- Non ho trovato issue o PR llama.cpp che segnalino la non-invarianza tinyBLAS F32 vs `vec_dot_f32` per `ssm_alpha/beta` di Qwen3.5 (ricerca non esaustiva).
- Non ho trovato misure dell'entità numerica della differenza: nessun numero riportato.

### Esperimenti suggeriti (in ordine)
1. Confermare i tipi del GGUF reale: `gguf-dump <file> | grep -E "ssm_(alpha|beta)"`.
2. Build con `-DGGML_LLAMAFILE=OFF`, poi rifare la verifica a T=2 (stesso seed e prompt).
3. Dump bit-esatto via `cb_eval`, con un tensore per layer (`alpha-<il>`, `beta-<il>`, `linear_attn_out-<il>`, `l_out-<il>`) per lo stesso token a T=1 e come riga 0/1 a T=2. Il primo tensore non bit-identico localizza il layer e l'op. Atteso: `alpha-0` / `beta-0`.
4. Separare V4 tenendo il contesto totale <512.
