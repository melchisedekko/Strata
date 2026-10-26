# Strata+: piano aggiornato e protocollo (H1, H2, H4) con metriche indipendenti dall'hardware

Versione 2 (2026-10-25). Sostituisce le parti hardware di `protocollo.md`: non c'è una GPU AMD.
Repo: github.com/Niko1221/Strata @ 7dd5cf18 (licenza MIT). Page di riferimento: "Strata+ — piano di ricerca speculative decoding", letta e non modificata.
Etichette usate in tutto il documento: **[S]** = implementato in Strata; **[A]** = esiste altrove (con link); **[P]** = solo plausibile.
Regola sui numeri: ogni numero viene dal repo, dalla Page o da una fonte con link. Le soglie decisionali sono marcate come **(decisione)**. Gli intervalli di sensibilità sono marcati come **(ipotesi)**.

---

## 0. Verifica di fattibilità: Strata compila su CPU?

- **Motore (`strata`): no.**
  - L'eseguibile è definito in `CMakeLists.txt:759`, dentro il blocco `if(STRATA_ENABLE_CUDA OR STRATA_ENABLE_HIP)` che si apre alla riga 335.
  - Gli altri backend non aiutano:
    - SYCL (`CMakeLists.txt:12-22`) è un progetto separato per Intel Arc (icpx + oneMKL, `docs/INTEL_ARC.md`).
    - Metal (`metal/`) gira solo su macOS.
  - Non esiste un backend CPU-only per il modello. I kernel in `src/kernels/cpu` servono solo agli expert offloadati.
- **Libreria della policy (`strata_spec`): sì.**
  - È la libreria statica "speculation components that need no GPU" (`CMakeLists.txt:1533-1536`): `suffix_drafter.cpp`, `controller.cpp`, `draft_policy.cpp`, `draft_source.cpp`.
  - L'ho compilata sul box con `zig c++ -std=c++20`, usando lo zig installato via pip nel venv di Strata Policy, perché sul box non ci sono g++/cmake di sistema.
  - Esito: `draft_policy_test` → `PASS`; `suffix_drafter_test` → `OK`.
  - Conseguenza pratica: il simulatore di replay può linkare **il codice di produzione** di `DraftPolicy` e `SuffixDrafter`, invece di una sua reimplementazione.
- **Risorse del box (condiviso):** 8 core e 15,6 GB di RAM. Al momento del controllo erano disponibili circa 2,2 GB, perché altri agenti erano attivi. Non ci sono torch né cmake. Questo vincola la scelta dei modelli proxy (§3).

## 1. Classificazione H1–H7 (riassunto)

| H | Stato | Evidenza | Testabile su CPU? |
|---|---|---|---|
| H1 arbitro MTP+lookup | [S] base: `DraftPolicy::choose` sceglie tra token/ms attesi, MTP vs lookup, con margine, probe e staleness (`src/spec/draft_policy.cpp:123-152`); catena con `--lookup-chain` (`:233-256`). [P] l'estensione con feature contestuali e feedback controfattuale | `generate.cpp:14880-14925` (serve), `16536-16582` (CLI) | Sì: replay con oracolo (§5) |
| H2 pool n-gram persistente cross-request | [S] solo l'aggancio: l'interfaccia `DraftSource` e il registro `extra_draft_sources()` (`include/strata/spec/draft_source.hpp:21-60`), usati solo con `--lookup-chain` (`generate.cpp:1089-1095`). Il suffix drafter viene resettato a ogni richiesta (`generate.cpp:14177-14178`). [A] llama.cpp `ngram-mod`: "a single hash pool is shared across all server slots" ([docs/speculative.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md)); vLLM suffix decoding; corpus Colibri (Scout) | | Sì: interamente offline sui token, senza modello |
| H3 expert MTP in Q8/Q4 | [S] il packing `tools/mtp_pack.py` supporta `--experts q2_0\|q4_0\|q8_0`, ma il runtime accetta solo Q2_0 (`tools/mtp_rt.py:49,72`). [P] il guadagno | | Solo come proxy: quantizzazione della testa MTP del proxy (esperimento extra E3) |
| H4 profondità dinamica | [S] parziale: `STRATA_SPEC_COST=1` attiva `keep_draft`/`draft_rate` per bucket di probabilità e per contesto (`draft_policy.cpp:184-224`, `generate.cpp:11179-11188`), più `--spec-min-p`. [A] LDLP/AdaEDL/SVIP (la Scout raccoglie i link). [P] il gate appreso | | Sì: replay con oracolo di profondità |
| H5 modello di costo expert-aware | [S] codice morto: `CostModel` in `include/strata/spec/controller.hpp:12-34`, che il motore non usa (lo usa solo il test). [P] il guadagno | | Solo come input del modello di costo (§4) |
| H6 DFlash2 | [S] nelle build CUDA **e HIP** (`CMakeLists.txt:339-340`, `include/strata/core/dflash2.hpp`). **Correzione alla Page**, che indica "CUDA/Metal" | | No: serve GPU. Fuori ambito |
| H7 FastMTP fine-tune | [A] FastMTP. Richiede il checkpoint BF16 da 335 GB (fonte: Page) | | No. Fuori ambito |

## 2. Fasi

| Fase | Contenuto | Responsabile | Uscita |
|---|---|---|---|
| F0 | Fattibilità (§0) e congelamento del formato di log (§6) | Coordinamento + Bench | Questo documento; `log_schema.json` |
| F1 | Tracce CPU: llama.cpp CPU più proxy con MTP nativo; riferimenti greedy y; proposte MTP teacher-forced a profondità Dmax | Bench | JSONL per dominio; hash dell'output |
| F2 | Simulatore di replay che linka `strata_spec`; validazione del simulatore contro il run live di llama.cpp | Policy (+ Bench) | `sim/` + report di validazione |
| F3 | Analisi dell'oracolo: gap di `DraftPolicy` attuale, `STRATA_SPEC_COST`, profondità fissa, pool H2 | Policy | Go/no-go per H1, H2, H4 (§8) |
| F4 | Progetto della policy: arbitro v2, pool, gate di profondità. Robustezza su 3 domini × 4 profili di costo | Policy (profili da Scout e Bench) | Policy candidata + intervalli di confidenza |
| F5 | Patch Strata **solo locale** (§9), test unitari compilati su CPU, replay deterministico. Nessun push e nessuna PR | Policy + Coordinamento | `git diff` locale + note per una futura validazione su GPU |

## 3. Modelli proxy (verificati il 2026-10-25)

**Requisito:** un target con testa MTP nativa che stia in circa 2 GB di RAM libera e giri con llama.cpp su CPU.
llama.cpp ha `--spec-type draft-mtp` ("Use Multi Token Prediction (MTP) heads from the main model", [docs/speculative.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md)), introdotto dalla [PR #22673](https://github.com/ggml-org/llama.cpp/pull/22673). Quella PR è stata testata su Qwen3.6 27B e 35B-A3B.

| Modello | MTP | Licenza | Su questo box? | Note |
|---|---|---|---|---|
| **Qwen3.5-0.8B** ([HF](https://huggingface.co/Qwen/Qwen3.5-0.8B); GGUF [unsloth/Qwen3.5-0.8B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.5-0.8B-MTP-GGUF), file Q4_K_M/Q8_0) | Sì (nativa) | Apache-2.0 | Sì | Proxy primario per l'iterazione veloce |
| **Qwen3.5-2B** ([HF](https://huggingface.co/Qwen/Qwen3.5-2B); [unsloth/Qwen3.5-2B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.5-2B-MTP-GGUF); Q8_0 2,08 GB secondo [prithivMLmods](https://huggingface.co/prithivMLmods/Qwen3.5-2B-MTP-GGUF)) | Sì: "MTP: trained with multi-steps" | Apache-2.0 | Q4_K_M sì; Q8_0 al limite | **Proxy principale.** Architettura ibrida Gated DeltaNet + Gated Attention, quindi stessa famiglia GDN di Qwen3.8 (stato GDN in `include/strata/core/verify.hpp`). È però **denso**, non MoE |
| MiMo-7B ([HF](https://huggingface.co/XiaomiMiMo/MiMo-7B-RL)) | Sì: "one MTP layer… acceptance rate is about 90%" | MIT | No: 8B parametri in BF16; supporto llama.cpp non verificato | Solo citazione |
| Qwen3.6-35B-A3B (MoE, MTP) | Sì | — | No: almeno 18 GB a 3 bit ([tabella Unsloth](https://unsloth.ai/docs/models/mtp)) | Sarebbe il proxy MoE più fedele; serve una macchina più grande |
| Gemma 4 E2B/E4B | MTP non supportato in llama.cpp per queste varianti ([PR #23398](https://github.com/ggml-org/llama.cpp/pull/23398)) | — | — | Escluso |
| Fallback: Qwen3-1.7B + EAGLE-3 ([AngelSlim/Qwen3-1.7B_eagle3](https://huggingface.co/AngelSlim/Qwen3-1.7B_eagle3), supportato da `draft-eagle3`) | Drafter esterno | da verificare | Probabilmente sì | Usarlo solo se la strada MTP fallisce |

**Limiti noti del proxy (da tenere a mente in ogni conclusione):**
- È denso, quindi non riproduce il costo degli expert mancati (verify.hpp:10-11). Questo effetto entra solo dal modello di costo (§4).
- La testa MTP del proxy non è quantizzata Q2 come in Strata (`mtp_rt.py:49,72`).
- Il tokenizer di Qwen3.8 rispetto a Qwen3.5 è una domanda aperta (Q3, §12).

## 4. Modello di costo parametrico

T_round(T, src) = c_verify(T) + c_mtp · d_mtp(src, T) + c_lookup · [src usa lookup/pool]

- T è la larghezza della finestra, cioè 1 + numero di draft.
- d_mtp è il numero di draft MTP generati. Quando si logga a profondità piena, il costo attribuito resta comunque T-1.

**Normalizzazione.** Si divide tutto per c_verify(1), ottenendo:
- la forma s(T) = c_verify(T)/c_verify(1);
- ρ_mtp = c_mtp/c_verify(1);
- ρ_lu = c_lookup/c_verify(1).

Il tok/s stimato è N / (Σ_round T_round). L'unità di misura è "passi da 1 token". Il **ranking tra policy dipende solo da (s, ρ_mtp, ρ_lu)** e non dalla velocità assoluta. Questo è ciò che rende le metriche indipendenti dall'hardware. Il tok/s assoluto si ottiene moltiplicando per 1/c_verify(1) di un hardware specifico.

**Profili di calibrazione, ognuno con la sua fonte:**

| Profilo | s(T) per T=1..8 | ρ_mtp | ρ_lu | Fonte |
|---|---|---|---|---|
| P1 "Strata-GPU prior" | 1; 1,35; 1,7; 2,05; 2,45; 2,85; 3,25; 3,6 | simbolico | simbolico | `kShape`, `src/spec/draft_policy.cpp:8-13`: "Between the RTX 5070's measured curves… (bench/results/2026-09-27-spec/window-cost)". **Quella directory non è nel repo.** |
| P2 "Controller 23-Sep" | derivato dalla formula `CostModel::step_ms` (`src/spec/controller.cpp:8-18`) con i default di `controller.hpp:26-34`: 1; 1,30; 1,67; 1,99; 2,43; 2,83; 3,25; 3,67 (calcolo mio da quei default, n=T) | 1,2/20,51 ≈ 0,059 | 0,01/20,51 ≈ 0,0005 | `controller.hpp:12-15`: dense ratio da "bench/results/2026-09-23-mmvq-multi", expert distinti da "2026-09-23-spec-economics". **Attenzione:** `dense_ms = 11.0` è etichettato "plan P3 target", quindi non è una misura. Anche le directory 2026-09-23-* non sono nel repo |
| P3 "Union degli expert" (solo per la componente CPU) | 1; 1,75; 2,4; 3,05 per T=1..4 | — | — | `include/strata/core/verify.hpp:10-11` ("measured on decode traces") |
| P4 "Proxy CPU misurato" | misurato da Bench con `llama-bench` sul box, Qwen3.5-2B, per T=1..8 | misurato | misurato | Misura interna: verifica la coerenza, non rappresenta Strata |
| B-flat / B-lin (limiti) | s(T)=1 / s(T)=T | — | — | **(ipotesi)**: estremi memory-bound e compute-bound |

**Analisi di sensibilità (ipotesi dichiarate):**
- s(T) sulla famiglia s_α(T) = 1 + α(T−1), con α ∈ [0, 1]. P1 e P2 cadono vicino ad α ≈ 0,35 per T piccoli (derivato dalle tabelle sopra).
- ρ_mtp ∈ [0; 0,3] **(ipotesi)**. Include P2 (0,059) e lascia margine per un MTP più lento sul device.
- ρ_lu ∈ [0; 0,01] **(ipotesi)**.
- Per ogni conclusione serve una mappa che indichi in quale regione di (α, ρ_mtp) la policy candidata batte la baseline.

**Numeri pubblici, non usati come parametri ma come verifica di coerenza:**
- Accettazione MTP 0,89/0,86/0,85 ai passi 1-3 (`include/strata/core/mtp.hpp:3-5`, tools/mtp_probe.py).
- Prior del Controller pari a 0,86 per draft (`controller.cpp:21-25`).
- "2.4-3.2 tokens/pass" con MTP fino a 3 draft (`docs/DETAILS.md:2303-2306`).
- Radeon 780M: `--spec 2` 15,65 tok/s, `--spec 4` 14,18, `--spec 6` 11,16 (`docs/RADEON_780M.md:110-113`).
- Varianza community: sweep su 2× RTX PRO 4500. Per esempio `--spec 5 kurz-code` ha un intervallo min-max di 121-134 tok/s su 3 run (`bench/results/2026-10-01-community-2x-rtx-pro-4500/spec-sweep/sweep-out.txt`). Questo giustifica metriche che non dipendono dal cronometro.

## 5. Metriche: definizioni operative

Definizioni comuni:
- Sia y l'output greedy di riferimento di una richiesta, cioè il target senza speculazione.
- La verifica in Strata è un match greedy di prefisso, bit per bit (`verify.hpp:1-8`; `generate.cpp:16646-16647`).
- Quindi l'accettazione di **qualunque** proposta d alla posizione i è a(d, i) = la lunghezza del prefisso comune tra d e y[i+1:], limitata a T−1. Questo vale anche per proposte che non sono state scelte (valutazione controfattuale).

**M1. Token accettati per verifica (AL).**
- AL = (Σ_r (a_r + 1)) / R, dove R è il numero di round di verifica.
- È equivalente all'"accepted per round" stampato da Strata (`generate.cpp:16727-16770`).
- Va riportato per dominio, insieme all'accettazione per posizione j: P(a ≥ j | T > j).

**M2. Margine rispetto all'oracolo.** Le opzioni per round sono Ω = {none (T=1); MTP con T=2..Dmax+1; lookup con T=2..k+1; chain MTP+lookup; pool (H2)}. Ci sono due oracoli:
- **O_round (miope, come chiesto):** a ogni posizione i visitata dalla policy, si prende max_ω (a_ω+1)/T_round(ω) col senno di poi.
- **O_DP (globale):** V(i) = min_ω [T_round(ω) + V(i + a_ω(i) + 1)], con V(|y|) = 0. Si calcola con programmazione dinamica su tutte le posizioni, possibile perché y è fisso. O_DP è il vero limite superiore.
- **Gap:** G = 1 − tps_policy / tps_oracle, in tok/s stimato con lo stesso profilo di costo. Va riportato sia per O_round sia per O_DP, per dominio e per profilo.
- **Gap di profondità (H4):** l'oracolo ristretto a "fonte fissata, T libero".

**M3. tok/s stimato.** È N / Σ_r T_round(T_r, src_r) sotto i profili P1–P4 e la griglia di sensibilità.
- **Speedup stimato** = (N · s(1)) / Σ T_round. È lo stesso concetto di "speedup vs --spec 1" indicato nella Page.

**M4. Righe sprecate.** Σ_r (T_r − 1 − a_r) / Σ_r (T_r − 1). È una metrica della Page.

**M5. Identità greedy.**
- Run live (llama.cpp con e senza spec): l'output deve essere byte per byte uguale a y (confronto via sha256).
- Simulatore: l'identità vale per costruzione. Il criterio diventa la concordanza tra simulatore e live (§8, V1).
- Strata: `--spec-follow` e i flag di riproducibilità (`docs/DETAILS.md:99-112`; issue #1928).

**Statistica.**
- L'unità di ricampionamento è la richiesta.
- Si usa un bootstrap al 95% sulle richieste per ogni differenza tra policy.
- Le metriche sono deterministiche dato y e il profilo, quindi non servono ripetizioni, salvo quelle per la validazione live V1.

## 6. Formato di log condiviso, per round (JSONL, obbligatorio per tutti)

C'è una riga `request` per richiesta, poi una riga `round` per ogni round di verifica. Il campo `engine` vale `strata`, `llamacpp` oppure `sim`.

```json
{"type":"request","schema":"strataplus.v1","run_id":"…","engine":"llamacpp","engine_rev":"<git sha>","model":"Qwen3.5-2B-Q4_K_M","flags":"…","dataset":"humaneval","domain":"code|chat|edit","req_id":"…","session_id":"…|null","turn":0,"prompt_sha256":"…","prompt_tokens":0,"output_sha256":"…","output_tokens":0,"ref_output_sha256":"…"}
{"type":"round","run_id":"…","req_id":"…","r":17,"pos":412,"ctx_len":1530,"ctx_bucket":0,
 "source":"none|mtp|lookup|chain|pool","k_proposed":3,"T":4,"proposal":[1,2,3],
 "cand":{"mtp":{"tokens":[…Dmax],"probs":[…Dmax]},
         "lookup":{"tokens":[…],"match":7},
         "pool":{"tokens":[…],"match":12,"origin_req":"…"}},
 "accepted":2,"committed":3,
 "ms_measured":null,
 "cost_est":{"profile":"P2","c_verify":1.99,"c_mtp":0.177,"c_lookup":0.0,"total":2.167},
 "policy":"draft_policy@7dd5cf18|arbiter_v2@…","policy_note":"probe|stale|margin"}
```

Regole:
1. Ogni round registra **tutte** le proposte candidate, comprese quelle non scelte. L'MTP va registrato a profondità piena Dmax, anche quando T è più piccolo. Senza questo non si può calcolare l'oracolo.
2. `accepted` è la lunghezza del prefisso comune con i token effettivamente committati.
3. `ms_measured` è facoltativo, perché l'hardware è rumoroso. `cost_est` è obbligatorio e viene ricalcolabile dal simulatore per qualsiasi profilo.
4. Per le tracce teacher-forced (F1) c'è una riga `round` per ogni posizione i, con `source:"none"` e `cand` pieno.
5. Mappatura dall'attuale `STRATA_SPEC_TRACE` ("T a sfx ms p1 p2…", `generate.cpp:16398-16405` e `16704-16707`, solo CLI): T→`T`, a→`accepted`, sfx→`source`, p*→`cand.mtp.probs`. Mancano i token, il lookup non scelto, la posizione e il serve. Va colmato con la patch P1 (§9).

## 7. Dataset (licenze verificate il 2026-10-25 dai tag HF / API GitHub)

| Dominio | Dataset | Licenza | Uso |
|---|---|---|---|
| code | [openai/openai_humaneval](https://huggingface.co/datasets/openai/openai_humaneval) | MIT | Completamento di funzioni |
| code | [google-research-datasets/mbpp](https://huggingface.co/datasets/google-research-datasets/mbpp) | CC-BY-4.0 | Programmi brevi |
| chat | [HuggingFaceH4/mt_bench_prompts](https://huggingface.co/datasets/HuggingFaceH4/mt_bench_prompts) | Apache-2.0 | Chat multi-turn |
| chat (mix) | [hemingkx/Spec-Bench](https://github.com/hemingkx/Spec-Bench) | Repo Apache-2.0. Le sottosorgenti hanno licenze proprie, **da verificare** prima di ridistribuire | Benchmark standard di speculative decoding |
| chat / estrattivo | [abisee/cnn_dailymail](https://huggingface.co/datasets/abisee/cnn_dailymail) | Apache-2.0 | Riassunto: stress test favorevole al lookup |
| edit | [edit_np](<URL non pubblicato>) | MIT | 105 task di edit Python con prima/dopo |
| edit | [bigcode/commitpackft](https://huggingface.co/datasets/bigcode/commitpackft) | Tag MIT, ma il codice resta sotto la licenza dei repo originari: solo uso interno | Edit da commit reali |
| edit / agentico | `tools/agent_turns_bench.py` (repo Strata, MIT) | MIT | Sessioni multi-turn sui file del repo. Ha temperatura 1, quindi **serve una variante greedy**. È il caso chiave per H2 |
| — | SWE-bench Lite | Licenza **non mostrata** nei tag HF: da verificare | Opzionale |

Per H2 contano due cose:
- l'ordine delle richieste e `session_id`;
- un controllo di contaminazione: problemi indipendenti (HumanEval) contro sessioni (agent_turns, edit_np prima→dopo).

## 8. Criteri go/no-go (indipendenti dall'hardware)

**V1, validazione del simulatore (gate di F2).** Sullo stesso prompt e su y, il simulatore con policy "MTP a profondità fissa k" deve riprodurre l'AL del run live di llama.cpp `--spec-type draft-mtp --spec-draft-n-max k`.
- Criterio: uguaglianza dei conteggi per round se il run live è greedy-deterministico. Altrimenti va riportata la discrepanza e si chiarisce l'ipotesi di indipendenza dal cammino del teacher forcing (Q2) prima di andare avanti.
- **(decisione)** Se V1 fallisce, F3 usa solo tracce live, non teacher-forced.

**H1 (arbitro).**
- **No-go** se G(O_round) di `DraftPolicy` attuale è < 3% su tutti e tre i domini e sotto P1 e P2. La soglia del 3% viene dalla Page e dalla richiesta.
- **Go** se l'arbitro v2 ha un guadagno di tok/s stimato rispetto a `DraftPolicy` con IC95 > 0 in almeno 2 domini su 3, nessun dominio con IC95 interamente < 0, e lo stesso segno sotto P1, P2 e P4 **(decisione)**.

**H2 (pool persistente).**
- **Go** se, sui dati a sessione (edit/agentico), il guadagno di AL e di tok/s stimato rispetto al lookup per richiesta ha IC95 > 0, e se su chat/HumanEval (richieste indipendenti) non c'è una regressione significativa (IC95 non interamente < 0) **(decisione)**.
- Va riportata anche la memoria del pool. Riferimento: llama.cpp `ngram-mod` dichiara "~16 MB" ([docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md)).

**H4 (profondità).**
- **No-go** se il gap rispetto all'oracolo di profondità (fonte fissata) di `STRATA_SPEC_COST=1` è < 3% su tutti i domini.
- **Go** se il gate candidato batte sia `STRATA_SPEC_COST=1` sia la profondità fissa k=3 (equivalente di `--spec 4`) con gli stessi criteri di IC e segno usati per H1.

**Robustezza (obiettivo finale).** La policy proposta deve essere ≥ baseline (IC95 non interamente < 0) in tutte le celle 3 domini × {P1, P2, P4, B-flat, B-lin}, e > baseline almeno sotto P1 e P2 **(decisione)**.

## 9. Patch proposta per Strata (solo locale, nessun push e nessuna PR)

- **P1, trace JSONL unificato** [P]: un nuovo `include/strata/spec/trace.hpp`, attivato da `STRATA_SPEC_JSONL=path`, nei percorsi CLI (`generate.cpp:16536-16715`) **e** serve (`14880-14925`). Registra tutte le candidate (§6). Con `STRATA_SPEC_TRACE_FULL=1` l’MTP genera draft fino a Dmax solo per il log (`mtp.hpp`, `set_max_drafts`).
- **P2, modalità deterministica della policy** [P]: `DraftPolicy` usa costi presi da una tabella, cioè lo stesso formato di `STRATA_SPEC_COST_TABLE` (`generate.cpp:16432-16446`), al posto dei ms misurati (EMA in `draft_policy.cpp:154-173`). Elimina il non-determinismo dovuto ai tempi (#1928) e rende identici replay e motore.
- **P3, arbitro v2 (H1)** [P]: nuove feature in `choose` (p1 MTP da `observe_probs`, bucket di match del lookup, bucket di contesto: tutto già presente in `draft_policy.cpp:32-96,184-197`) più un aggiornamento controfattuale.
  - Attenzione: nel motore l'accettazione della proposta non scelta è **censurata** a a+1 token committati.
  - Va quindi aggiornata in ritardo nei round successivi, quando y è noto più avanti.
- **P4, pool persistente (H2)** [P, meccanismo A in llama.cpp]: una `PoolSource : DraftSource` registrata in `extra_draft_sources()` (`draft_source.hpp:55`) a livello di processo, alimentata con prompt e output a fine richiesta, con memoria limitata (hash rolling come `ngram-mod`).
  - Le sorgenti vanno abilitate anche fuori da `--lookup-chain`. Oggi `propose_from_sources` si usa solo lì (`generate.cpp:1089-1095`).
  - Il reset per richiesta (`14177`) resta per il suffix drafter locale.
- **P5, gate di profondità (H4)** [S, estensione]: si riusano `keep_draft`/`draft_rate` (`draft_policy.cpp:184-224`) con soglia appresa per bucket di contesto, valutata nel replay.
- **Verifica locale:** la build di `strata_spec` più i test con `zig c++` (§0), un nuovo `trace_test` e `pool_source_test`, e un replay deterministico (stesso JSONL in ingresso, stesse scelte in uscita). Il motore non è compilabile qui: la validazione su GPU resta fuori ambito e va documentata.

## 10. Chi fa cosa e cosa serve da ciascuno

- **Strata Policy**
  - Compiti: simulatore di replay che linka `strata_spec` (già compilabile con zig), oracoli O_round e O_DP, valutazione di H1, H2 e H4, policy candidata, patch P2–P5.
  - **Mi serve:** il modo di iniettare i costi del profilo in `DraftPolicy::observe`, e il risultato di V1.
- **Strata Bench**
  - Compiti: build CPU di llama.cpp con `draft-mtp`, download di Qwen3.5-0.8B/2B MTP GGUF, riferimenti greedy y, tracce teacher-forced nel formato §6, profilo P4 via `llama-bench`, run live per V1, varianti greedy di `agent_turns_bench`.
  - **Mi serve:** sapere se llama.cpp espone i token draft per round. Altrimenti serve una patch locale di logging su llama.cpp, anche questa senza push. Serve anche il budget RAM concordato sul box condiviso.
- **Strata Scout**
  - Compiti: numeri pubblici per s(T), ρ_mtp e ρ_lu di Strata o di motori simili (con link); meccanismi di Colibri (corpus/gate), llama.cpp `ngram-mod`/`ngram-map`, vLLM suffix e MTP, EAGLE e gate di profondità (LDLP/AdaEDL/SVIP); conferma di altri proxy con MTP.
  - **Mi serve:** per ogni parametro, un valore con link oppure "non trovato", così il parametro resta simbolico con sensibilità.

## 11. Esperimenti fuori piano (1–3)

- **E1, limite superiore model-free per H2.** Accettazione di lookup e pool calcolata solo sui token di y, con `SuffixDrafter` reale contro un pool cross-request. Non serve nessun modello e si può fare subito.
- **E2, sensibilità al tokenizer.** Lo stesso testo tokenizzato con il tokenizer del proxy e con quello di Qwen3.8 (se disponibile), per stimare se la lunghezza dei match del lookup si trasferisce dal proxy a Qwen3.8.
- **E3, proxy per H3.** La testa MTP di Qwen3.5-2B quantizzata a Q8_0, Q4 e Q2 in GGUF, misurando l'accettazione per posizione con teacher forcing. Indica la direzione, non è trasferibile in valore assoluto.

## 12. Domande aperte e blocchi

1. **Q1: RAM del box.** Erano disponibili circa 2,2 GB su 15,6 durante il controllo. Il 2B in Q8_0 è al limite: serve coordinarsi con gli altri agenti.
2. **Q2: indipendenza dal cammino del teacher forcing.** In Strata lo stato MTP e lo stato GDN si aggiornano con replay (`verify.hpp`), quindi le draft MTP alla posizione i potrebbero dipendere dalla storia delle finestre. Il gate V1 serve a verificarlo.
3. **Q3:** tokenizer e dimensioni MTP di Qwen3.8-Flash-Next rispetto a Qwen3.5. La licenza HF di Qwen3.8 è "other".
4. **Q4: provenienza dei costi nel repo.** Le directory citate come fonte dei costi (`bench/results/2026-09-23-*`, `2026-09-27-spec/window-cost`) non sono nel repo, e `dense_ms` è un target, non una misura. P1 e P2 sono quindi "prior pubblicati nel codice", non misure riproducibili.
5. **Q5:** llama.cpp `draft-mtp` su CPU: prestazioni ed esposizione delle draft per round (non verificato).
6. **Q6:** il proxy è denso e Qwen3.8 è MoE. L'effetto degli expert entra solo via P2/P3: è sufficiente?
7. **Q7:** la licenza delle sottosorgenti di Spec-Bench e di SWE-bench Lite è ancora da verificare.
8. **Correzione alla Page:** DFlash2 è disponibile in CUDA **e HIP** (`CMakeLists.txt:339-340`), non "CUDA/Metal". Va segnalata al lead: la Page non è stata modificata.
