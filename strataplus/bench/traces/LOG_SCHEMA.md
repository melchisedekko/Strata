# LOG_SCHEMA — tracce per round `strataplus.v1` prodotte da Strata Bench

**Riferimento normativo:** `/workspace/strata-plus/log_format.md` (Strata Policy, v1, allineato a piano.md §6).
Questo file non definisce uno schema nuovo: dice quali campi produciamo, da dove vengono e dove divergiamo.
Etichetta: **proxy CPU** (llama.cpp, Qwen3.5-2B-MTP) — non numeri AMD.

## Pipeline
1. `proxy/llama_spec_trace` (llama.cpp d327bf1f + `patches/llamacpp-draft-mtp-probs.patch`) scrive righe grezze in
   `/workspace/strata-plus/traces/raw/<run_id>.jsonl` (round…, poi request).
2. `tools/annotate.py` le converte in `/workspace/strata-plus/traces/<run_id>.jsonl`: riga `request` per prima, poi i
   `round` in ordine; aggiunge `ref_tokens` (= y del run `base_r0`), sha256, `acc`, `cost_est` (profilo P4 misurato).
3. `tools/summarize.py` → `SUMMARY.md` / `summary.json`; `tools/cost_p4.py` → `cost_p4_cpu.json`.

## Riga `request` (tutti i campi obbligatori di log_format §1.1 presenti)
`type, schema, run_id, engine="llamacpp", engine_rev, model, flags, dataset, domain, req_id, session_id=null, turn=0,
prompt_sha256, prompt_tokens, output_sha256, output_tokens, ref_output_sha256, data_kind (live|teacher_forced),
dmax, ref_tokens, prompt_ids` + extra: `label="proxy CPU"`, `rep`, `greedy_equal_ref` (output == y),
`stats` (verify_rounds, drafted, accepted, prefill_ms, decode_ms, draft_ms, verify_ms, mtp_process_ms).

## Riga `round`
`r, pos` (= token di output già committati, D4), `kv_pos` (extra: posizione KV di id_last), `ctx_len` (= prompt+pos),
`ctx_bucket` (soglie 6000/24000), `source` (`none|mtp|lookup`; `replay` mai emesso con questo modello perché
`use_ckpt_tgt=0`), `k_proposed, T, proposal, cand.mtp{tokens,probs}, cand.lookup{tokens,match}|null, accepted,
committed=accepted+1, ms_measured` (somma dei timer), `ms_split{verify, mtp, mtp_draft, mtp_process, lookup, commit=null}`,
`cost_est{profile:"P4-cpu-2b", c_verify=s(T), c_mtp=rho_mtp, c_lookup=rho_lu, d_mtp, total}`, `policy, policy_note=""`,
`acc{mtp,lookup}` (LCP con y[pos:], non troncato a T−1), `censored{false,false}`, extra: `domain`, `target_tokens`
(token del target dalla verifica del round).

## Divergenze / note (da segnalare a Strata Policy / Lead)
- **G1 — `cand.mtp` a Dmax solo nel teacher-forced.** Nei run live `--spec-draft-n-max k` l'MTP di llama.cpp genera solo
  k token: `cand.mtp.tokens` ha lunghezza k (= `request.dmax` del run), non 7. Le candidate a profondità piena
  (Dmax=7) per **ogni** posizione sono in `tf_d7.jsonl` (`data_kind="teacher_forced"`, `source:"none"`, `T:1`,
  regola 4). Generare 7 draft in ogni round live cambierebbe il costo misurato del run live (serve al gate V1).
- **G2 — `cand.mtp.probs`** = probabilità top‑1 del sampler MTP di llama.cpp, che è `top_k=10` + temperatura
  (`common/speculative.cpp:65-69`): la probabilità è rinormalizzata sui 10 candidati, quindi **sovrastima** la
  softmax piena. `cand.mtp.ent` (D11) **non** è prodotto (servirebbe la softmax completa, non esposta da questo sampler).
- **G3 — lookup** = `strata::spec::SuffixDrafter` reale (strata-src @7dd5cf18, `min_match=3, max_match=32`, costruttore di default; `strata generate` usa invece `SuffixDrafter(max(1,--suffix-draft), 64, …)`, `generate.cpp:16428`),
  `propose(7)` su prompt+committati, calcolato **ogni round** (anche quando la fonte è MTP). `cand.lookup=null` se nessun match.
- **G4 — `cand.pool` / `cand.chain`** non prodotti (H2/--lookup-chain non simulati nel proxy).
- **G5 — config `combo`**: regola Strata-like (strata-src `generate.cpp:16556-16563`): lookup se il suo primo token
  coincide col primo draft MTP e propone più token dell'MTP; altrimenti MTP. Non è `DraftPolicy::choose` (vedi PROTOCOL.md).
- **G6 — sha256**: `prompt_sha256` / `output_sha256` = sha256 della stringa degli id separati da virgola (non del testo).
- **G7 — `ms_*`**: tempi CPU, solo per rapporti relativi. `cost_est` usa il profilo P4 misurato (`cost_p4_cpu.json`).
- **G8 — identità greedy non garantita sul backend CPU.** Misurato: base vs base 30/30, tf_d7 vs base 30/30, ma verifica a T>1
  cambia deterministicamente l'argmax in alcune posizioni (diag_yright/ywrong: 6/12 prompt divergono nelle stesse posizioni,
  con e senza rollback). Per questo `annotate.py` calcola `acc` contro l'output del run stesso (`acc_ref='self_output'`),
  aggiunge `first_divergence_pos` alla riga request e `after_divergence` alle righe round. Dettagli: traces/GREEDY_DIAG.md.
- **G9 — bug di fine sequenza nel proxy.** Nell'ultimo round `n_draft_max=0` ⇒ `dp.n_max=0` = "nessun limite"
  (common/speculative.cpp:1869, :3025) ⇒ MTP propone 7 token anche con k<7 (llama_spec_trace.cpp:92 imposta
  `draft.n_max=max(n_max,dmax)`). Round affetti: combo 24, k1 11, k2 15, k3 33, k5 13; esclusi da AL e V1
  (`excluded_endcap_rounds`), binario non corretto.
- **G10 — `cost_est`** = s(T) + d_mtp·rho_mtp + rho_lu dal profilo P4 2B Q4_K_M (proxy CPU, modello denso, non AMD).

## Aggiornamento 25/10 07:40 CET — campi aggiunti (check_v12, holdout_lookup_v12, agent_v12)
- **license** (riga header e request): licenza della sorgente del prompt. holdout: humaneval MIT, mt-bench Apache-2.0 (FastChat),
  edit_np MIT sulla card (licenza in conflitto, non pubblicabile); agent_v12: "MIT (Strata LICENSE, …)" per i contenuti dei file del repo Strata; SYSTEM/task/TOOLS da
  tools/agent_turns_bench.py dello stesso repo.
- **spec_params** (scritto da tools/annotate_v11.py `spec_meta`, oppure da post_holdout_lookup_v12.py):
  `draft_p_min` (+`draft_p_min_source`, `draft_p_min_compared_to`), `draft_n_min` (+`_source`), `draft_n_max_cli`,
  `draft_n_max_impl` = max(cli, dmax) perché il proxy imposta `draft.n_max = max(n_max, dmax)` (+`draft_n_max_impl_note`).
  holdout_lookup_v12: drafter `strata::spec::SuffixDrafter(min_match=3,max_match=64)::propose(max_k=dmax)`, `lookup_min_match` 3,
  `lookup_max_match` 64, `draft_n_max` = `draft_n_max_impl` = n (7/12/16), `draft_n_min` 0, `draft_p_min` 0.0 (non usato nel lookup).
- **Candidati TF solo fino a Dmax=7:** nei run `tf_d7` le candidate registrate per round (`cand.mtp.tokens`, `cand.lookup.tokens`)
  hanno al più 7 token (verificato su check_v12_tf_d7.jsonl: max 7 per entrambe). Accettanze per T>8 non sono ricostruibili da
  queste tracce.
- **Campi v12** (proxy/llama_spec_trace_v12.cpp, riga request): `raw_prompt` (true = prompt tokenizzato così com'è, senza chat
  template; dataset `raw:'1'`), `vmrss_kb`, `vmhwm_kb` (da /proc/self/status a fine richiesta), `n_ctx` (49152 per agent_v12).
- **truncation** (agent_v12, da tools/prepare_agent_v12_trunc.py, copiato in ogni riga request da tools/post_agent_v12.py):
  `{ctx_limit, token_budget, original_tokens, kept_tokens, truncated, dropped_turns, tool_result_cut}`. token_budget = 49013 =
  ctx − n_predict − dmax − 4 (regola di skip proxy/llama_spec_trace_v12.cpp:170). Si eliminano le coppie tool più vecchie
  mantenendo system+task; se resta solo la coppia corrente e non basta, il risultato tool corrente è tagliato alle prime N righe con
  marcatore `... (truncated: lines 1-N of M)` (`tool_result_cut`), come in agent_turns_bench.
- **k_cap** nei round combo con `source="lookup"`: vale mtp_k ma il draft può arrivare a dmax (vedi GREEDY_DIAG.md, nota k_cap).
- agent_v12 header: anche `build` {binary, binary_sha256, source, source_sha256, ggml_libs (LLAMAFILE OFF)} e `ctx_limit`.

## Aggiornamento 25/10 08:10 CET — semantica committed (proxy CPU, non AMD)
- v11/v12 (tutti i file pubblicati finora): `committed` = token emessi dal verify del round, anche oltre il primo EOG; `accepted` = committed-1. Il loop di output si ferma all'EOG, quindi in rari round finali sum(committed) > output_tokens. Errata: traces/holdout_lookup_v12_ERRATA.md.
- agent_v12 (clamp in post, tracer v12 invariato): regola `committed = min(committed_raw, output_tokens - pos); accepted = min(accepted_raw, committed); AL di round = min(accepted+1, committed)`. Round toccati: campi `committed_raw`, `accepted_raw`, `eos_clamped:true`; `committed_clamped_at_eos` nell'header (totale) e in ogni request; `eos_clamp_rule` in AGENT_V12_READY.
- v13 (E4 in poi, proxy/llama_spec_trace_v13.cpp = v12 + clamp nel tracer): `committed` = token fino al primo EOG incluso; `accepted = min(ids-1, committed)`; nuovi campi round `committed_raw` (= ids.size(), valore v11/v12) e `eos_clamped`; `n_accept` del request limitato allo stesso modo; request row con `"tracer":"llama_spec_trace_v13 (committed clamped at EOG)"`. Con v13 l'AL di round va letto come `committed` (accepted+1 resta sovrastimato di 1 nel solo round in cui l'EOS e' un draft accettato).
