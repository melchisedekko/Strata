# Strata+ — Ricognizione stato dell'arte speculative decoding (scout v1)

Data: 2026-10-25, ora Europe/Rome (UTC+2). Regola: nessuna fonte, numero, file o PR senza link. Ciò che non ho trovato è segnato **non trovato**; ciò che ho letto ma non eseguito è segnato **non verificato a runtime**.
Etichette: **[S]** implementato in Strata · **[A]** implementato altrove · **[P]** solo proposto (paper o idea).
Colonna hardware: **portabile** (gira anche su CPU) / **legato a HW** (CUDA-only, GPU ecc.).

Commit analizzati (tutti i permalink puntano qui):
- Strata `7dd5cf18e68c639a8773e096c5c79f971ea2a9f5` (MIT) — https://github.com/Niko1221/Strata
- Colibri `e0db083cdc9e563e0766cc6fc661ef23c32298e0` (Apache-2.0) — https://github.com/JustVugg/colibri
- llama.cpp `d327bf1f0780f87b8c01b367b61853b0c291d7c4` (MIT) — https://github.com/ggml-org/llama.cpp
- vLLM `4e591657157a021cab997f911d67f50c0d18a71e` (Apache-2.0) — https://github.com/vllm-project/vllm
- SGLang `656331295619a4d0267b40b7da0b5cd5b549fcbc` (Apache-2.0) — https://github.com/sgl-project/sglang

---

## Proxy per Strata Bench (vincolo: CPU, ≤ ~6 GB GGUF; nuovo vincolo RAM libera ~2,2 GB)

**In sintesi:** l'affermazione di Strata Lead è **confermata**. Qwen3.5-0.8B e Qwen3.5-2B hanno una testa MTP nativa e la licenza è Apache-2.0. I GGUF `unsloth/*-MTP-GGUF` contengono davvero i tensori `nextn`, e llama.cpp ha il supporto MTP per l'arch `qwen35` già merged. **Non verificato a runtime:** non ho eseguito llama.cpp su CPU con `--spec-type draft-mtp`.

| # | Proxy | Repo HF (verificato via API) | Quantizzazione consigliata (dimensione dall'albero file HF) | Sta in ~2 GB? | Licenza |
|---|---|---|---|---|---|
| 1 | **Qwen3.5-2B + MTP nativo** (proxy principale) | [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) sha 15852e8c · GGUF [unsloth/Qwen3.5-2B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.5-2B-MTP-GGUF) | `Qwen3.5-2B-Q4_K_M.gguf` 1,33 GB · Q4_0 1,26 · Q5_K_M 1,47 · Q6_K 1,63 · **Q8_0 2,08** | Q4_K_M sì (1,33 GB di pesi; KV e buffer di calcolo **non misurati**). Q8_0 no (2,08 GB solo di file) | Apache-2.0 (tag HF e `general.license` nel GGUF) |
| 2 | **Qwen3.5-0.8B + MTP nativo** (iterazione veloce) | [Qwen/Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B) sha 2fc06364 · GGUF [unsloth/Qwen3.5-0.8B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.5-0.8B-MTP-GGUF) | `Qwen3.5-0.8B-Q8_0.gguf` 0,83 GB (consigliata) · Q4_K_M 0,55 | Sì, anche in Q8_0 | Apache-2.0 |
| 3 | Qwen3.5-4B + MTP nativo (stesso hidden 2560 di Flash-Next) | [unsloth/Qwen3.5-4B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.5-4B-MTP-GGUF) sha 86835bf9 | Q4_K_M 2,84 GB · Q3_K_M 2,38 · UD-IQ2_M 1,94 | **No** con ~2,2 GB liberi. Va bene se la RAM torna disponibile (entro i 6 GB) | Apache-2.0 |
| 4 | Coppia target + drafter: Qwen3.5-2B (target) + Qwen3.5-0.8B (drafter, `-md`) | target come #1; drafter [unsloth/Qwen3.5-0.8B-GGUF](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF) (senza MTP) | 1,33 + 0,53 GB (Q4_K_M) | Al limite (1,86 GB di soli file) | Apache-2.0 |
| 5 | Drafter alternativi già pubblicati per Qwen3.5-4B (solo se c'è RAM) | DFlash [z-lab/Qwen3.5-4B-DFlash](https://huggingface.co/z-lab/Qwen3.5-4B-DFlash) (Apache-2.0, 1,27 GB safetensors), GGUF [Anbeeld/Qwen3.5-4B-DFlash-GGUF](https://huggingface.co/Anbeeld/Qwen3.5-4B-DFlash-GGUF) (Q4_K_M 0,38 GB); EAGLE-3 [yuyijiong/Qwen3.5-4B-Eagle3](https://huggingface.co/yuyijiong/Qwen3.5-4B-Eagle3) (Apache-2.0, 0,47 GB) | — | No (target 4B) | Apache-2.0 |

**Verifiche fatte:**
- **Tensori MTP nel GGUF.** Ho letto l'header GGUF via HTTP Range con lo script `/workspace/scout/gguf_tensors.py`.
  - Per `Qwen3.5-0.8B-Q4_K_M.gguf` e `Qwen3.5-2B-Q4_K_M.gguf` dei repo `-MTP-GGUF`:
    - `general.architecture = qwen35`, `qwen35.block_count = 25`, `qwen35.nextn_predict_layers = 1`;
    - i tensori `blk.24.nextn.{eh_proj,enorm,hnorm,shared_head_norm}.weight`, più un blocco attention+FFN completo in `blk.24`;
    - vocabolario di 248320 token.
  - Controllo negativo: il GGUF non-MTP `unsloth/Qwen3.5-0.8B-GGUF` ha 24 blocchi e 0 tensori `nextn`.
- **Config HF.** `mtp_num_hidden_layers = 1` e `vocab_size = 248320` sia per 0.8B sia per 2B. Il vocabolario è lo stesso di Qwen/Qwen3.8-Flash-Next (248320, verificato in precedenza).
- **llama.cpp.**
  - La [PR #22673 "llama + spec: MTP Support"](https://github.com/ggml-org/llama.cpp/pull/22673) è **merged** il 2026-05-16 alle 14:06 (Europe/Rome). È anche il commit `255582687b` che tocca `src/models/qwen35.cpp`.
  - Seguono [#24025 "qwen35: use post-norm hidden state for MTP"](https://github.com/ggml-org/llama.cpp/pull/24025) e [#27694](https://github.com/ggml-org/llama.cpp/pull/27694) (drafter probabilistico + rejection sampling per MTP, merged il 2026-10-02).
  - Codice: caricamento dei tensori nextn in [src/models/qwen35.cpp#L114-L119](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/src/models/qwen35.cpp#L114-L119) e `nextn_flags` in [#L36-L38](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/src/models/qwen35.cpp#L36-L38).
  - Il flag `draft-mtp` è in [docs/speculative.md#L227](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/docs/speculative.md#L227) e [#L372](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/docs/speculative.md#L372), mappato in [common/speculative.cpp#L78](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L78).
- **Strata non gira su CPU.** Il motore richiede CUDA/HIP/SYCL/Metal: [docs/release-notes-0.2.2.md#L60](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/docs/release-notes-0.2.2.md#L60) dice che "the CUDA, HIP and SYCL engines cannot start" con la scelta CPU-only. Quindi il proxy CPU passa da llama.cpp, mentre la policy di Strata (`strata_spec`) va usata in replay offline.
  - Strata ha un engine `qwen35` per Qwen3.6-35B-A3B ([docs/QWEN36.md#L1-L6](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/docs/QWEN36.md#L1-L6)), ma è solo GPU.
  - La [PR #3908 "qwen35: MTP drafting for sampled requests"](https://github.com/Niko1221/Strata/pull/3908) è aperta.

**Scartati:**
- **MiMo-7B** ([XiaomiMiMo/MiMo-7B-RL](https://huggingface.co/XiaomiMiMo/MiMo-7B-RL), MIT, [MiMo-7B-MTPs](https://huggingface.co/XiaomiMiMo/MiMo-7B-MTPs)): vocabolario 151680, diverso da Flash-Next. In llama.cpp esiste solo l'arch `mimo2` ([src/llama-arch.cpp#L155](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/src/llama-arch.cpp#L155)); `MiMoForCausalLM` non risulta in `convert_hf_to_gguf.py` → MTP MiMo-7B in llama.cpp **non trovato**.
- **Qwen3-4B + Qwen3-0.6B** ([unsloth/Qwen3-4B-GGUF](https://huggingface.co/unsloth/Qwen3-4B-GGUF) Q4_K_M 2,50 GB; [unsloth/Qwen3-0.6B-GGUF](https://huggingface.co/unsloth/Qwen3-0.6B-GGUF) Q4_K_M 0,40 GB; Apache-2.0): vocabolario 151936, diverso da Flash-Next, e niente MTP. Peggiore di Qwen3.5 come proxy.

**Limiti del proxy:** Qwen3.5 0.8B e 2B sono densi, mentre Flash-Next è MoE con 512 esperti. Il costo degli expert mancati non viene riprodotto.

---

## 1. Richieste di Specu

### 1.1 Gate MTP+lookup: Colibri vs `DraftPolicy::choose`

**[S] Strata:** [src/spec/draft_policy.cpp#L123-L152](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_policy.cpp#L123-L152).
- Il valore MTP è `base = mtp_tokens(t)/cost_ms(t)`, con la finestra `t_mtp` **fissata dal chiamante**.
- Per il lookup prova k = 1..min(lookup_k, max_t−1) con E(k) = 1+q+…+q^k e r = E/cost_ms(k+1).
- Sceglie il lookup solo se r > base·(1+margin).
- La q del lookup è per bucket di match (<6/<12/<24, [#L32-L34](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_policy.cpp#L32-L34)) ed è stimata come (ok+4·prior)/(ok+bad+4) ([#L36-L39](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_policy.cpp#L36-L39)).
- I prior sono kPriorQ {0,75; 0,88; 0,93; 0,96} ([#L20](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_policy.cpp#L20)).
- Probe kProbes = 3 e staleness 300 round ([#L22-L25](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_policy.cpp#L22-L25), [#L145-L150](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_policy.cpp#L145-L150)).
- Bucket di contesto 6000/24000 ([#L76-L96](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_policy.cpp#L76-L96)).
- Osservazione EMA ([#L154-L173](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_policy.cpp#L154-L173)).

**[A] Colibri:**
- [c/spec_draft.h#L129-L160](https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/c/spec_draft.h#L129-L160) massimizza **anche la profondità MTP** su k, con prior per posizione; `SPEC_PROBE 16` (un draft più profondo ogni 16 scelte) e `SPEC_REFRESH 64` ([c/spec_draft.h#L42-L46](https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/c/spec_draft.h#L42-L46)).
- [c/qwen38_core.h#L3883-L3893](https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/c/qwen38_core.h#L3883-L3893) sceglie il lookup se vl>vm, oppure se sono pari e il lookup è più lungo: tutto o niente, senza margine.

**Differenze chiave:**
- Colibri sceglie insieme la profondità MTP; Strata la riceve fissa (oppure la sceglie con `STRATA_SPEC_COST=1`, vedi §2).
- Strata ha margine, bucket per match e per contesto, e staleness.

**Origine del +13% Colibri:** la tabella in [docs/speculative.md#L187-L198](https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/docs/speculative.md#L187-L198).
- Run: prompt di code edit da 160 token, Qwen3.8 su CPU.
- Riga "MTP at the gate's depth + lookup": 3,30 tok/s (+13%) contro 2,91 senza draft, con 2,74 token/forward.
- Confronto: MTP con 1 draft dà +10%, il solo lookup +7%. Con MTP a 1 draft + lookup, "lookup never chosen" (L196).
- Quindi il +13% viene dalla **profondità MTP scelta dal gate**, non dal lookup. Colibri stesso scrive "Their gains therefore do not add" ([#L229-L232](https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/docs/speculative.md#L229-L232)).
- Hardware: Ryzen 7 PRO 8700GE ([#L159](https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/docs/speculative.md#L159)).
- La tabella non riporta ripetizioni per Qwen3.8. **Non trovato** uno script che riproduca il numero.

### 1.2 llama.cpp: draft-mtp + draft-eagle3 insieme? Più `--spec-type`

**[A] Parsing.** `--spec-type` accetta una lista separata da virgole ([common/arg.cpp#L4322-L4331](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/arg.cpp#L4322-L4331)) con nomi validati ([common/speculative.cpp#L2428-L2445](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L2428-L2445): "none" azzera, un nome sconosciuto dà errore) e una bitmask ([#L2492-L2498](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L2492-L2498)). Esempio documentato: `--spec-type ngram-mod,ngram-map-k4v` ([docs/speculative.md#L384-L387](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/docs/speculative.md#L384-L387)).

**Combinazione: fallback a priorità fissa, non cost-aware.**
- Ordine: ngram-simple, map-k, map-k4v, mod, cache, draft-simple, eagle3, mtp, dflash, dspark ([#L2806-L2818](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L2806-L2818)).
- Il primo impl che produce un draft vince ([#L2975-L3063](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L2975-L3063)). Gli altri ricevono `accept` con is_other ([#L3065-L3099](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L3065-L3099)).
- La documentazione lo conferma: draftless "has higher precedence" ([docs/speculative.md#L207](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/docs/speculative.md#L207)), e un impl con draft model "can be mixed with" uno senza ([#L9](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/docs/speculative.md#L9)).

**mtp + eagle3:** c'è un solo `model_dft`/`ctx_dft` ([#L2704-L2762](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L2704-L2762)). Con draft-mtp il contesto è di tipo MTP. Quindi i due tipi si possono passare insieme, ma **non** come due drafter indipendenti: al massimo un fallback eagle3→mtp sullo stesso contesto. **Non verificato a runtime.** L'auto-inferenza dal sidecar ha priorità mtp > dspark > dflash > eagle3 ([common/arg.cpp#L555-L572](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/arg.cpp#L555-L572)).

### 1.3 Strata #1161 e PR DFlash (tutte nel repo Niko1221/Strata; in llama.cpp, vLLM e SGLang gli stessi numeri sono oggetti non correlati)

- **[#1161](https://github.com/Niko1221/Strata/issues/1161)** "Port ngram-mod & other ngram-* …":
  - aperta da Interpause il 2026-10-06 alle 15:39:48 (Europe/Rome);
  - **chiusa da Niko1221 il 2026-10-13 alle 23:55:43 (Europe/Rome)**, `not_planned`;
  - chiusura in blocco delle issue più vecchie di 3 giorni dopo la v0.1.44, senza PR né commit collegati;
  - Interpause ha contestato la chiusura il 2026-10-14 alle 05:48 (Europe/Rome).
- **[PR #1426](https://github.com/Niko1221/Strata/pull/1426)** (j-luwierski, DFlash standalone):
  - **chiusa senza merge** il 2026-10-19 alle 18:42:59 (Europe/Rome), per il reset del tracker 0.2.0-beta ("Closed here does not mean rejected");
  - nella review di Niko1221 DFlash risulta 15-35% dietro MTP su RTX PRO 5000.
- **[PR #3322](https://github.com/Niko1221/Strata/pull/3322)** (checkpoint ufficiale DFlash2): **aperta**. "MTP and DFlash2 cannot be selected together".
- **[PR #3457](https://github.com/Niko1221/Strata/pull/3457)** (Metal `--dflash`): **aperta**, nessun commento.
- **DFlash2 è già in main**, aggiunto dal maintainer con il commit `7f97c35a` (2026-10-21 14:04, Europe/Rome). È solo nelle build CUDA e HIP ([CMakeLists.txt#L339-L340](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/CMakeLists.txt#L339-L340)) → **legato a HW**.

### 1.4 Pool n-gram persistente tra richieste: vedi §3.

---

## 2. Modello di costo (numeri con fonte)

Parametri del piano v2 (`/workspace/strata-plus/piano.md` §4):
- s(T) = c_verify(T)/c_verify(1);
- ρ_mtp = costo di un passo MTP / forward del target;
- ρ_lu = costo del lookup / forward del target.

### 2.1 Numeri pubblici o misurati, con fonte

| Parametro | Valore | Condizioni (modello, HW, batch, T) | Fonte (link esatto) |
|---|---|---|---|
| s(T) | **non trovato** come curva pubblica per Qwen-Next / Flash-Next | — | — |
| s(T) componente CPU (expert mancati) | 1; 1,75; 2,4; 3,05 per T=1..4 | Qwen3.8-Flash-Next in Strata, misurato "on decode traces", HW non indicato | [Strata include/strata/core/verify.hpp#L10-L11](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/core/verify.hpp#L10-L11). Commento nel codice, i dati grezzi non sono nel repo |
| ρ_mtp | **non trovato** come rapporto pubblicato per Qwen-Next, MiMo, DeepSeek-V3 o EAGLE | — | — |
| ρ_lu (lookup n-gram) | durate totali ngram_mod b/g/a = 0,149 / 0,347 / 0,005 ms su 810 chiamate | esempio di log nella doc llama.cpp; modello e HW non indicati | [llama.cpp docs/speculative.md#L434](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/docs/speculative.md#L434), definizione in [#L447](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/docs/speculative.md#L447) |
| ρ_lu (ngram-map-k) | dur b/g/a = 2,234 / 1,427 / 0,016 ms (calls 6/1690/26) | come sopra | [docs/speculative.md#L438](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/docs/speculative.md#L438) |
| ρ_lu (suffix tree) | "~20 microseconds per token" di draft, su CPU | SuffixDecoding, workload agentici | [arXiv:2411.04975 (HTML)](https://arxiv.org/html/2411.04975) |
| Accettazione MTP (per E[accettati]) | 85-90% sul 2° token; circa 1,8× TPS | DeepSeek-V3, 1 modulo MTP | [arXiv:2412.19437](https://arxiv.org/abs/2412.19437). Sezione esatta **non verificata** |
| Accettazione MTP | circa 90% con 1 layer MTP | MiMo-7B | [arXiv:2505.07608](https://arxiv.org/abs/2505.07608). Pagina e sezione **non verificate** |
| Accettazione MTP per posizione | 0,88 al token 0 e 0,18 al token 1; lunghezza media accettata 2,06 con 2 draft | MiMo-7B in vLLM (test della PR) | [vllm PR #25136](https://github.com/vllm-project/vllm/pull/25136). Valori presi dal riassunto di ricerca, **da rileggere nella PR** |
| Accettazione MTP Flash-Next | 0,89 / 0,86 / 0,85 ai passi 1-3 | Qwen3.8-Flash-Next, greedy, `tools/mtp_probe.py` | [Strata include/strata/core/mtp.hpp#L3-L5](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/core/mtp.hpp#L3-L5) |
| Token per pass | 2,4-3,2 con MTP fino a 3 draft | Strata, Flash-Next | [Strata docs/DETAILS.md#L2303-L2306](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/docs/DETAILS.md#L2303-L2306) |
| Speedup DFlash2 vs MTP | +29,05% code short; +14,84% a 256K (decode) | RTX 4070 Ti SUPER, Flash-Next | body della [PR #3322](https://github.com/Niko1221/Strata/pull/3322) |
| Speedup DFlash2 vs MTP | 58,96/59,62 vs 52,53/53,00 tok/s a 16 token; servizio 110,7 vs 84,0 tok/s | R9700 gfx1201, ROCm nightly | commento di bsorensen110 (2026-10-20, 21:20 Europe/Rome) nella [PR #3322](https://github.com/Niko1221/Strata/pull/3322) |
| Speedup EAGLE-3 | fino a 6,5×; circa 1,4× su EAGLE-2; 1,38× throughput in SGLang a batch 64 | dal paper | [arXiv:2503.01840](https://arxiv.org/abs/2503.01840) |

### 2.2 Costi citati nel codice di Strata — **stima/obiettivo nel codice, non misura pubblica**

| Parametro | Valore nel codice | Cosa dice il codice | Permalink | Dati grezzi nel repo? |
|---|---|---|---|---|
| s(T) "kShape" | 1; 1,35; 1,7; 2,05; 2,45; 2,85; 3,25; 3,6 (T=1..8) | "Between the RTX 5070's measured curves … (bench/results/2026-09-27-spec/window-cost)"; usato solo per le larghezze non ancora misurate | [src/spec/draft_policy.cpp#L10-L13](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_policy.cpp#L10-L13) | **No**: `bench/results/2026-09-27-spec` non esiste (esistono solo -cache-parity, -esp, -kv-q4) |
| dense_ms | 11,0 ms | "one-token dense pass (**plan P3 target**)" → obiettivo, non misura | [include/strata/spec/controller.hpp#L26](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/controller.hpp#L26) | — |
| dense_ratio(n) | 1,0; 1,05; 1,3; 1,45; 1,85; 2,2; 2,6; 3,0; 3,3 | "23 Sep measurements … native MMVQ (bench/results/2026-09-23-mmvq-multi)" | [controller.hpp#L12-L15](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/controller.hpp#L12-L15), [#L27](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/controller.hpp#L27) | **No** (nessuna directory 2026-09-23-mmvq-multi) |
| distinct_ratio U(n)/U(1) | 1,0; 1,70; 2,31; 2,88; 3,40; 3,89; 4,35; 4,80; 5,2 | "routing trace (2026-09-23-spec-economics)" | [controller.hpp#L30](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/controller.hpp#L30) | **No** |
| cpu_all_miss_ms / hit_rate / extra_use_cost | 15,8 ms / 0,55 / 0,25 | "extra-token CPU cost 0.2-0.35 (2026-09-23-cpu-expert-multi)" | [controller.hpp#L28-L31](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/controller.hpp#L28-L31) | **No** |
| sync_ms | 2,4 ms | default | [controller.hpp#L32](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/controller.hpp#L32) | — |
| mtp_draft_ms → ρ_mtp | 1,2 ms per token → ρ_mtp = 1,2/20,51 ≈ 0,059 (20,51 = step_ms(0) con i default; calcolo mio dalla formula) | default | [controller.hpp#L33](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/controller.hpp#L33), formula [src/spec/controller.cpp#L8-L18](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/controller.cpp#L8-L18) | — |
| lookup_draft_ms → ρ_lu | 0,01 ms per token → ρ_lu ≈ 0,0005 | default | [controller.hpp#L34](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/controller.hpp#L34) | — |
| prior MTP / lookup | 0,86 per draft; lookup {0,35; 0,6; 0,8; 0,92} da "offline replay (2026-09-23-suffix-lookup)" | prior | [src/spec/controller.cpp#L21-L24](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/controller.cpp#L21-L24) | **No** |
| `STRATA_SPEC_COST=1` | finestra MTP per token/ms attesi ai costi di riga misurati (braccio A/B); `STRATA_SPEC_COST_TABLE` precarica una tabella | — | [src/program/generate.cpp#L11179](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/program/generate.cpp#L11179), [#L16400-L16432](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/program/generate.cpp#L16400-L16432), [include/strata/spec/draft_policy.hpp#L27](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/draft_policy.hpp#L27), [#L51-L62](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/draft_policy.hpp#L51-L62) | — |
| Effetto del lookup | "Code edits +6-11%, ordinary text unchanged (bench/results/2026-09-27-spec)" | — | [src/program/generate.cpp#L3205-L3207](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/program/generate.cpp#L3205-L3207) | **No** |

Nota: `CostModel`/`Controller` sono usati solo dai test e non dal motore (piano v2 H5). I profili B-flat (s=1) e B-lin (s=T) sono **ipotesi**, non fonti.

---

## 3. Pool n-gram persistenti e profondità adattiva

### 3.1 Pool n-gram / retrieval cross-request

| Meccanismo | Stato | Dove (link + righe) | Persistenza | Licenza | HW |
|---|---|---|---|---|---|
| **Gancio in Strata** | [S] solo l'interfaccia; **nessuna sorgente registrata** | `DraftSource` + `extra_draft_sources()` [include/strata/spec/draft_source.hpp#L1-L55](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/draft_source.hpp#L1-L55) ("a retrieval store over a codebase or earlier conversations"); scelta per match più lungo [src/spec/draft_source.cpp#L13-L34](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_source.cpp#L13-L34); `reset()` a ogni richiesta [src/program/generate.cpp#L1089-L1095](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/program/generate.cpp#L1089-L1095) | Un pool persistente deve ignorare `reset()` | MIT | portabile (la lib `strata_spec` compila su CPU) |
| llama.cpp **ngram-mod** | [A] merged ([#19164](https://github.com/ggml-org/llama.cpp/pull/19164) "spec : add ngram-mod", 2026-01-30 17:21 Europe/Rome) | [docs/speculative.md#L162-L197](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/docs/speculative.md#L162-L197) ("a single hash pool is shared across all server slots", L176); [common/ngram-mod.h#L1-L38](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/ngram-mod.h#L1-L38); 4·1024·1024 entry ([common/speculative.cpp#L2033-L2060](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L2033-L2060)); reset all'occupazione > 0,25 ([#L2089-L2103](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L2089-L2103), [#L2180-L2200](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L2180-L2200)) | Tra richieste, in RAM; **non** su file | MIT | portabile |
| llama.cpp **ngram-cache** (lookup) | [A] merged ([#5479](https://github.com/ggml-org/llama.cpp/pull/5479), 2024-03-23) | [common/ngram-cache.h#L9-L11](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/ngram-cache.h#L9-L11), save/load/merge [#L84-L101](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/ngram-cache.h#L84-L101); `-lcs`/`-lcd` [common/arg.cpp#L1635-L1648](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/arg.cpp#L1635-L1648); caricamento e salvataggio [common/speculative.cpp#L2236-L2287](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L2236-L2287) | **Su file** (statica + dinamica) | MIT | portabile |
| **SuffixDecoding** (Arctic Inference) | [A] in vLLM e Arctic; paper [arXiv:2411.04975](https://arxiv.org/abs/2411.04975) (NeurIPS 2025 spotlight) | vLLM [vllm/v1/spec_decode/suffix_decoding.py#L9-L102](https://github.com/vllm-project/vllm/blob/4e591657157a021cab997f911d67f50c0d18a71e/vllm/v1/spec_decode/suffix_decoding.py#L9-L102) (`SuffixDecodingCache` con `max_cached_requests`, speculazione dinamica `max_spec_factor`/`min_token_prob`); codice [snowflakedb/ArcticInference](https://github.com/snowflakedb/ArcticInference) | Albero globale delle risposte passate + albero per richiesta (in RAM) | Apache-2.0 | portabile (CPU) |
| **SGLang NGRAM corpus** | [A] | un unico `NgramCorpus` per worker, alimentato da tutte le richieste ([python/sglang/srt/speculative/ngram_worker.py#L114-L123](https://github.com/sgl-project/sglang/blob/656331295619a4d0267b40b7da0b5cd5b549fcbc/python/sglang/srt/speculative/ngram_worker.py#L114-L123), `batch_put` [#L410-L420](https://github.com/sgl-project/sglang/blob/656331295619a4d0267b40b7da0b5cd5b549fcbc/python/sglang/srt/speculative/ngram_worker.py#L410-L420), reset solo in `clear_cache_pool` [#L150-L152](https://github.com/sgl-project/sglang/blob/656331295619a4d0267b40b7da0b5cd5b549fcbc/python/sglang/srt/speculative/ngram_worker.py#L150-L152)); trie con capacity 1.000.000 di default ([cpp_ngram/ngram_corpus.py#L14-L24](https://github.com/sgl-project/sglang/blob/656331295619a4d0267b40b7da0b5cd5b549fcbc/python/sglang/srt/speculative/cpp_ngram/ngram_corpus.py#L14-L24)); corpora SAM esterni caricabili ([external_corpus_manager.py#L1-L33](https://github.com/sgl-project/sglang/blob/656331295619a4d0267b40b7da0b5cd5b549fcbc/python/sglang/srt/speculative/external_corpus_manager.py#L1-L33)) | Tra richieste, in RAM; corpus esterno da file | Apache-2.0 | portabile (corpus lato CPU) |
| **Lookahead decoding** | [P]/[A] codice di ricerca | [arXiv:2402.02057](https://arxiv.org/abs/2402.02057); [hao-ai-lab/LookaheadDecoding](https://github.com/hao-ai-lab/LookaheadDecoding) | pool n-gram per generazione (non verificato se cross-request) | Apache-2.0 | portabile in principio |
| **REST** | [P]/[A] codice di ricerca | [arXiv:2311.08252](https://arxiv.org/abs/2311.08252); [FasterDecoding/REST](https://github.com/FasterDecoding/REST) | datastore statico da corpus | Apache-2.0 | portabile |
| **PLD** (prompt lookup) | [A] | [apoorvumang/prompt-lookup-decoding](https://github.com/apoorvumang/prompt-lookup-decoding); paper arXiv **non trovato** | solo il prompt corrente | **nessuna licenza dichiarata** su GitHub (license=null) | portabile |

### 3.2 Profondità / selezione adattiva del draft

| Meccanismo | Idea | Paper | Codice / licenza | Stato |
|---|---|---|---|---|
| Strata `STRATA_SPEC_COST` + `--spec-min-p` | finestra MTP per token/ms attesi, catena interrotta dalla probabilità | — | vedi §2.2 (MIT) | [S] braccio A/B, opt-in |
| Colibri gate | massimizza su k sia per MTP sia per lookup | — | [c/spec_draft.h#L129-L160](https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/c/spec_draft.h#L129-L160) (Apache-2.0) | [A] |
| SGLang adaptive steps | EMA della lunghezza accettata → target = round(EMA)+1 tra candidati per batch size, con isteresi; solo EAGLE/EAGLE3 topk=1 | — | [python/sglang/srt/speculative/adaptive_spec_params.py#L153-L262](https://github.com/sgl-project/sglang/blob/656331295619a4d0267b40b7da0b5cd5b549fcbc/python/sglang/srt/speculative/adaptive_spec_params.py#L153-L262), default [#L28-L53](https://github.com/sgl-project/sglang/blob/656331295619a4d0267b40b7da0b5cd5b549fcbc/python/sglang/srt/speculative/adaptive_spec_params.py#L28-L53), vincoli [#L56-L80](https://github.com/sgl-project/sglang/blob/656331295619a4d0267b40b7da0b5cd5b549fcbc/python/sglang/srt/speculative/adaptive_spec_params.py#L56-L80) (Apache-2.0) | [A] |
| vLLM Dynamic SD | numero di token speculativi per intervallo di batch size | — | [vllm/v1/spec_decode/dynamic/utils.py](https://github.com/vllm-project/vllm/blob/4e591657157a021cab997f911d67f50c0d18a71e/vllm/v1/spec_decode/dynamic/utils.py) (Apache-2.0) | [A], non approfondito |
| SuffixDecoding | numero di token in funzione della lunghezza del match e della probabilità | [arXiv:2411.04975](https://arxiv.org/abs/2411.04975) | Apache-2.0 | [A] |
| **AdaEDL** | stop quando il limite inferiore 1−√(γH) dell'accettazione, calcolato dall'entropia del draft, scende sotto λ; training-free; +10-57% rispetto alla lunghezza statica | [arXiv:2410.18351](https://arxiv.org/abs/2410.18351) (Qualcomm, workshop ENLSP @ NeurIPS 2024) | codice **non trovato** | [P] |
| **SVIP** | stop se √H_q > h (entropia del draft); fino a +17% su MT-Bench a 8K | [arXiv:2411.18462](https://arxiv.org/abs/2411.18462) (EMNLP 2025) | [Geralt-Targaryen/SVIP](https://github.com/geralt-targaryen/svip/) MIT | [P]/[A] ricerca |
| **AdaEAGLE** | predittore leggero LDLP della lunghezza di draft ottimale; 1,62× rispetto ad AR | [arXiv:2412.18910](https://arxiv.org/abs/2412.18910) | codice **non trovato** | [P] |
| **Learning to Draft (LTD)** | RL (PPO) su policy di profondità e di dimensione della verifica, con reward = token accettati/tempo | [arXiv:2603.01639](https://arxiv.org/abs/2603.01639) (ICLR 2026) | [zhzihao/Learning-to-Draft](https://github.com/zhzihao/Learning-to-Draft) Apache-2.0 | [P] |
| **HedgeSpec = "Not-a-Bandit"** (stesso paper) | selezione online del drafter in full-information (Hedge/NormalHedge): valuta tutti i drafter senza chiamate extra al target; fino a +83,7% tok/s rispetto a EAGLE in un singolo dominio | [arXiv:2510.20064](https://arxiv.org/abs/2510.20064) | [aladinggit/hedgespec](https://github.com/aladinggit/hedgespec) Apache-2.0 | [P] — rilevante per MTP vs lookup vs pool, con feedback controfattuale |
| **DSpark** | testa di confidenza che prevede l'accettazione per posizione e permette una lunghezza di verifica adattiva | [arXiv:2607.05147](https://arxiv.org/abs/2607.05147) | in llama.cpp [#25173](https://github.com/ggml-org/llama.cpp/pull/25173) "spec: add DSpark speculative decoding" (merged 2026-07-28) | [A] |

Altri paper: EAGLE-3 [arXiv:2503.01840](https://arxiv.org/abs/2503.01840) ([SafeAILab/EAGLE](https://github.com/SafeAILab/EAGLE), licenza GitHub "NOASSERTION"); DFlash [arXiv:2602.06036](https://arxiv.org/abs/2602.06036) ([z-lab/dflash](https://github.com/z-lab/dflash) MIT).

---

## 4. Tabella delle idee prioritarie

| Idea | Fonte (link+righe) | Licenza | Hardware | Stato | Sforzo | Prossimo passo |
|---|---|---|---|---|---|---|
| 1. Pool n-gram persistente come `DraftSource` (stile ngram-mod o suffix tree globale) | gancio [draft_source.hpp#L1-L55](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/include/strata/spec/draft_source.hpp#L1-L55); riferimenti [llama.cpp ngram-mod](https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/common/speculative.cpp#L2033-L2060), [vLLM suffix](https://github.com/vllm-project/vllm/blob/4e591657157a021cab997f911d67f50c0d18a71e/vllm/v1/spec_decode/suffix_decoding.py#L9-L102) | MIT / Apache-2.0 | portabile | [S] gancio, [A] altrove | medio | replay offline su tracce Qwen3.5-2B multi-turno |
| 2. Gate congiunto profondità MTP + lookup (stile Colibri) dentro `DraftPolicy` | [draft_policy.cpp#L123-L152](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/src/spec/draft_policy.cpp#L123-L152); [Colibri spec_draft.h#L129-L160](https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/c/spec_draft.h#L129-L160) | MIT / Apache-2.0 | portabile | [A] in Colibri, [S] parziale (`STRATA_SPEC_COST`) | basso-medio | oracolo O_DP sul replay |
| 3. Stop per entropia/probabilità del draft MTP (AdaEDL/SVIP) | [arXiv:2410.18351](https://arxiv.org/abs/2410.18351), [arXiv:2411.18462](https://arxiv.org/abs/2411.18462) | SVIP MIT | portabile | [P] (Strata ha `--spec-min-p`) | basso | logging delle prob MTP per posizione |
| 4. Selezione full-information tra sorgenti (HedgeSpec) | [arXiv:2510.20064](https://arxiv.org/abs/2510.20064) | Apache-2.0 | portabile | [P] | medio | valutazione controfattuale già prevista dal log v1 |
| 5. DFlash2 come sorgente alternativa | commit 7f97c35a; [CMakeLists.txt#L339-L340](https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/CMakeLists.txt#L339-L340) | Apache-2.0 (checkpoint incoai) | **legato a HW** (CUDA/HIP) | [S] | — | fuori ambito CPU |

---

## 5. Non trovato / non verificato

- Curva pubblica s(T) e rapporto ρ_mtp per Qwen-Next / Flash-Next, MiMo, DeepSeek-V3 o EAGLE: **non trovati**.
- `bench/results/2026-09-27-spec` e tutte le directory `2026-09-23-*` citate nel codice: **non presenti** nel repo Strata @7dd5cf18.
- Codice ufficiale di AdaEDL e di AdaEAGLE: **non trovato**. Paper di PLD su arXiv: **non trovato**; repo senza licenza.
- "HedgeSpec" e "Not-a-Bandit" non sono due paper distinti: sono lo stesso lavoro (arXiv:2510.20064).
- Esecuzione reale di llama.cpp `--spec-type draft-mtp` su CPU con Qwen3.5-0.8B/2B: **non verificata a runtime** (verificati solo codice, PR e tensori GGUF). Footprint RAM oltre la dimensione file: **non misurato**.
- mtp+eagle3 insieme in llama.cpp: dedotto dal codice, **non verificato a runtime**.
- Numeri della PR vLLM #25136 (MiMo): presi dal riassunto di ricerca, da rileggere nella PR. Sezioni esatte di DeepSeek-V3 e MiMo: **non verificate**.
- Script che riproduce il +13% di Colibri: **non trovato**.
- RAM: al momento di questo controllo `free -g` mostrava 8 GB "available" (il valore cambia con gli altri agenti). Ho usato il vincolo di ~2,2 GB indicato da Strata Lead.
