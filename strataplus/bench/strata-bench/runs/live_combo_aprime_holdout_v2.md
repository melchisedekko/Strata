# Run file — (a') vs default (a), live con arbitro, holdout 90 (proxy CPU, non AMD)
**Versione 2** (26/10/2026 CET), sostituisce live_combo_aprime_holdout.md (8df75e27…) e il suo script (5066b06a…). Nessuno dei due è stato lanciato. Unica modifica: la regola edit_np (§0). Prima versione scritta alle 19:40 CET. **Questo file e lo script sono scritti e hashati, NON lanciati.** Si lancia solo su richiesta esplicita, dopo E4 v14 (lo script controlla `e4v14.done`).
Lo script si lancia con `cd /workspace/strata-bench && nohup bash runs/run_live_combo_aprime_holdout_v2.sh &`. Tutti gli input sono verificati con sha256 all'avvio: se uno è cambiato, la run si ferma.
Cartella nuova `runs/`: contiene solo questo file e lo script, senza dati. Gli output vanno in `/workspace/strata-plus/traces/raw/aprime_holdout_v14/`, sotto traces/raw che esiste già.

## 0. Regola edit_np (decisione di Alessandro, 26/10 19:45 CET)
- **Ogni artefatto NUOVO derivato dal dominio edit/edit_np deve avere `edit_np` nel nome del file o della cartella.** Vale per tracce per richiesta, token, prompt, ID e metriche per richiesta. Così le esclusioni del sync lo prendono in automatico.
- **Nei report vanno solo aggregati per dominio.** Niente ID, token o valori per richiesta del dominio edit fuori dai file `*edit_np*`.
- Come lo applica lo script:
  - prompt divisi in `datasets/holdout_90_codechat.jsonl` (60 code+chat) e `datasets/holdout_90_edit_np.jsonl` (30 edit). La concatenazione è identica byte per byte a holdout_90.jsonl (739fbb9c…), quindi l'ordine resta lo stesso;
  - ogni braccio gira in due passate: `<tag>` (code+chat) e `<tag>_edit_np`. Lo stato dell'arbitro si resetta a ogni prompt, quindi le scelte sono le stesse di una passata unica;
  - i controlli scrivono `validity_cand_mtp_live_vs_tf[_edit_np].json/.out` e `aprime_post[_edit_np].json/.out`.
- Gli input esistenti che contengono dati edit per richiesta non vengono rinominati: hanno già uno sha256 annunciato. Sono ref_holdout_tf.tsv, holdout_tf_d7.jsonl, holdout_90.jsonl e mtp_cap_prefix_check.json, e sono elencati nel report.

## 1. Cosa si misura
Si misura solo l'AL (accepted length), più i controlli di coerenza e di validità. **Nessun tempo è un risultato**: i tempi del proxy CPU non sono trasferibili ad AMD (cfr. traces/AMD_PROTOCOL_v3.md).
Il ±3% confronta il replay di Policy con la nostra run live, sulla stessa politica, e non dice nulla sulla velocità. La scelta fra i bracci su AMD resta nell'AMD_PROTOCOL (regola H-LW).

| braccio | equivalente Strata | S | S_mtp | spec_min_p | lookup |
|---|---|---|---|---|---|
| (a') `--live-src aprime` | `--spec 8 --mtp-max-t 4` | 8 | 4 | 0 | propose(7) |
| default (a) `--live-src default_a` | `--spec 4 --spec-min-p 0.5` → auto spec+2 (generate.cpp L3208-3210) | 6 | 4 | 0.5 | propose(5) = prefisso di propose(7) |

**Flag comuni** (holdout_lookup_v12/cmds.txt, con tracer v14):
`-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512 --no-repack --dmax 7 --spec-draft-n-max 3 --prompts datasets/holdout_90_codechat.jsonl` (seconda passata: `--prompts datasets/holdout_90_edit_np.jsonl`, tag `<tag>_edit_np`)
- La parte live aggiunge `--mode live --live-src aprime|default_a --ref /workspace/strata-plus/traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv`.
- Il TF cap 3 usa `--mode tf --live-src mtp`.
- Ordine di esecuzione: (0) `holdout_tf_cap3_v14`, `holdout_tf_cap3_v14_edit_np`; (1) `aprime_holdout_v14`, `aprime_holdout_v14_edit_np`; (2) `default_a_holdout_v14`, `default_a_holdout_v14_edit_np`.
- 1 ripetizione. Il determinismo è verificato: live_mtp_k3 r0 vs r1 coincide in 1181/1181 posizioni (mtp_cap_prefix_check.json).
- nice 19, un solo processo llama, pre-check CPU, monitor CPU e finestre START/END in campaign.log e cpu_busy_bench.log.

## 2. Input fissati (sha256, verificati dallo script)
| file | sha256 |
|---|---|
| proxy/llama_spec_trace.v14.nollamafile (GGML_LLAMAFILE=OFF, libs build-nollamafile) | e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e |
| proxy/llama_spec_trace_v14.cpp | ddea7320ba99054810275d0228c89d1d0b93abd7ab0e1e5584507e739b048283 |
| **proxy/strata_arbiter_v1.hpp** (arbitro, file separato) | 85bb5341d9995d495bd2dd72ba52349ccccbed4497eeb00da67e1b500d8e7c19 |
| **proxy/strata_arbiter_v1.py** (port Python identico, per il replay di Policy) | 2b0e8b9a0c45d6927dca09db8f352a288305f5521e0c874ff45d4c87bf46611a |
| /workspace/llama.cpp/build-nollamafile/bin/libllama-common.so.0.7.0 | ef3d929534cecb1c60dcb5953bb44452a75a6b91dd69cb2b09569dbde51d59f7 |
| models/qwen35-2b-mtp-q4_k_m.gguf | 18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b |
| datasets/holdout_90.jsonl (= traces/holdout_lookup_v12/holdout_90.jsonl) | 739fbb9c606c881122f1426091aa47dc7f59873176405951b2e7aa7b0febdcb3 |
| traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv | 0a86e4679f75c4a2aaf1361d7d1b742d374ac7489aae82daf93a3e349c040a9d |
| traces/raw/v11_holdout/holdout_tf_d7.jsonl (TF cap 7, riferimento del replay; sha verificato il 26/10) | a16cf384f1dc5c06cbb5ae544051293413fa016fc3a1710401fad62b6ccad854 |
| traces/mtp_cap_prefix_check.json | 349866f270653c9fdced2e8a13a6b9fe94f1f0136aeb015b8c30640acb002ef2 |
| tools/mtp_cap_prefix_check.py | 42dd8621503ef07dbea6e34d1ca22791e001fed95062d7970898a81b6fc8b993 |
| tools/aprime_post.py | 808ebcc95997fef256bb4f3642f5740ff2aa6c4755a3c34750c20eecaab82e3e |
| datasets/holdout_90_codechat.jsonl | 18288525fff122efc9790efbeadcbf810ae5c650149833ea5cb8a141efdba84e |
| datasets/holdout_90_edit_np.jsonl | 6b2404c8b4d5de552c8faf1f27dc09d2b59ceb62721d5a76f5a769c1ed2739f2 |
| runs/run_live_combo_aprime_holdout_v2.sh | e1140052619d4dd9c672c96f0926f0399c113f21382595d6e7f2813067c51ace |

**Codice Strata citato:** /workspace/strata-src @ 7dd5cf18e68c639a8773e096c5c79f971ea2a9f5, licenza MIT.
- draft_policy.cpp: 890649e3c85891acd8c3e7d6de5908591bc81ef92732ecbe6547008efd61224a
- draft_policy.hpp: eef7a6ee17753a7c5368b12b5f049c5b325be4bd7844b731803ef4f00b876d92
- generate.cpp: 12d39e8e6817db694f08af1b52171bce2375c117c669cce8fb82d860c6ed59a2

**Scout:** scout_patch_support.md §11/§11.1 (sha256 3fb9c3b4…, osservato alle 19:29) e §11.2 (sha256 e2a51166…, come riportato dal parent). Il file è in modifica, quindi conta lo sha citato.

## 3. Ordine dei prompt (= ordine del file; verificato uguale all'ordine delle richieste in holdout_lookup_v12_n7)
30 code (HumanEval), 30 chat (MT-Bench, 1° turno), 30 edit (edit_np). Lo stato appreso si resetta a ogni prompt, quindi l'ordine non cambia le scelte. Va comunque fissato per il replay.
1:HumanEval/2, 2:HumanEval/13, 3:HumanEval/23, 4:HumanEval/28, 5:HumanEval/30, 6:HumanEval/34, 7:HumanEval/35, 8:HumanEval/52, 9:HumanEval/55, 10:HumanEval/59, 11:HumanEval/62, 12:HumanEval/71, 13:HumanEval/73, 14:HumanEval/82, 15:HumanEval/88, 16:HumanEval/91, 17:HumanEval/95, 18:HumanEval/101, 19:HumanEval/102, 20:HumanEval/106, 21:HumanEval/110, 22:HumanEval/111, 23:HumanEval/112, 24:HumanEval/133, 25:HumanEval/136, 26:HumanEval/142, 27:HumanEval/147, 28:HumanEval/148, 29:HumanEval/149, 30:HumanEval/152, 31:mtbench-84, 32:mtbench-93, 33:mtbench-94, 34:mtbench-97, 35:mtbench-99, 36:mtbench-100, 37:mtbench-101, 38:mtbench-105, 39:mtbench-106, 40:mtbench-107, 41:mtbench-109, 42:mtbench-113, 43:mtbench-115, 44:mtbench-116, 45:mtbench-121, 46:mtbench-122, 47:mtbench-123, 48:mtbench-129, 49:mtbench-132, 50:mtbench-134, 51:mtbench-136, 52:mtbench-139, 53:mtbench-140, 54:mtbench-145, 55:mtbench-146, 56:mtbench-152, 57:mtbench-153, 58:mtbench-157, 59:mtbench-159, 60:mtbench-160; 61–90: i 30 prompt edit_np nell'ordine di datasets/holdout_90_edit_np.jsonl (ID non elencati qui per la regola §0)

## 4. Arbitro: risposte dal codice (Strata @7dd5cf1)
1. **Chiamata applicata.** CLI, non serve. Il blocco serve (L8354-15693) chiama choose a L14471 e L14900; la run CLI usa `policy.choose` a **generate.cpp L16560**.
   - Il gate è L16556-16559: `k > 0 && sbuf[0] == drafts[0]`. Probe e staleness stanno dentro `DraftPolicy::choose` (draft_policy.cpp; kProbes 3 con q ≥ 0.85, kStaleRounds 300).
2. **s(T) fisso, senza EMA.** `cost_ms(t) = s[clamp(t,1,8)]` con s = kShape {1, 1.35, 1.7, 2.05, 2.45, 2.85, 3.25, 3.6} (draft_policy.cpp L13-25).
   - Contano solo i rapporti: la scala si annulla in base = mtp_tokens(T)/s(T) e in E(k)/s(k+1).
   - In Strata il costo è un'EMA (kCostAlpha 0.1) partita da spec_cost (set_robust, L16447; seed L16432). Qui non è usata: il proxy non ha tempi AMD.
   - C'è un solo bucket di contesto: `set_context` non fa nulla senza robust_.
   - Alternativa opzionale: `--arb-s s1,..,s8`, solo con un profilo misurato di cui si citano percorso e sha. Nessun profilo è fissato oggi.
3. **rho** = `margin_` = 0.03: il lookup vince se best > base·(1+0.03).
4. **Reset.** Lo stato appreso si resetta per prompt: `DraftPolicy policy(o.spec)` è locale al processo CLI (L16426-16429), e il tracer ricrea `sparb::Arbiter` a ogni prompt (v14 L199). L'ordine è quello della §3.
5. **AL.** Si riportano sia somma/somma sia la media per prompt. **Criterio: somma/somma per dominio**, sui domini code ed edit; chat si riporta e basta.

**Specifica completa per round** (proxy/strata_arbiter_v1.hpp; Policy deve usare la stessa nel replay):
- **Primo round** (first_window, L16551, pack nativo): T=1, nessuna choose e nessuna observe (observe solo se !first_window, L16585).
- **T di partenza:** T = S_mtp = 4 (L16536).
  - Con spec_min_p > 0 (default (a)): T=1, poi T++ finché p_MTP[T-1] ≥ 0.5 in float32, fino a S_mtp (L16538-16542).
  - p = `cand.mtp.probs` (top-1 softmax full-vocab a temp 1, vedi le deviazioni).
- **Gate** (L16556-16559): k_used = min(k_full, S-1) > 0 e lookup[0] == mtp[0]. Se passa, si chiama choose(T, k_used, match) (L16560).
- **Fallback (gate falso, oppure choose sceglie MTP):** finestra MTP con T = 4 (a') o T da min_p (default (a)).
  - pk.t si ignora; solo pk.lookup riassegna T (L125, L16561).
  - Il round si registra come MTP (L16714). T = min(T, room) (L16567-16568), T_mtp = T (L16583), finestra = draft MTP (L16592-16594).
- **Lookup scelto:** finestra = lookup[0..T-2].
- **observe** dopo ogni round non-first_window (L16714):
  - cost_n_[T] += 1, last_[T] = rounds_, rounds_ += 1;
  - lookup: ok_/bad_ del bucket di match con decadimento 0.97;
  - MTP: EMA mtp_tok_ con alfa 0.05;
  - il costo NON si aggiorna (s fisso).
  - Così stale() e i probe dopo 300 round si comportano come nel motore.
- **Priors:** kPriorQ {0.75, 0.88, 0.93, 0.96}, kPriorN 4. Bucket di match: <6, <12, <24, resto.

## 5. Deviazioni note del proxy (da citare con ogni numero)
1. È una **copia** dell'arbitro, non codice Strata eseguito: modello llama.cpp d327bf1f (draft-mtp) su CPU, non il motore Strata su AMD.
2. I costi in ms non sono trasferibili; s(T) è fisso (kShape). **Su AMD choose usa l'EMA (kCostAlpha 0.1) sui tempi reali, quindi le scelte possono differire da questa run e dal replay.**
3. room = 1 + n_draft_max include i token rimasti (fix G9). Strata limita solo con il contesto (L16567).
4. Probabilità MTP:
   - nel proxy è il top-1 della softmax full-vocab a temp 1 dei logit MTP;
   - la definizione di h_prob_ in Strata non è verificata;
   - le probabilità si scrivono con 5 decimali, quindi il replay da log può invertire casi a ridosso di 0.5 (pesa sul ≥99%).
5. first_window è modellato come pack nativo, con T=1.
6. Il lookup è SuffixDrafter(3,64) di Strata su prompt + output (k cap 7).
7. llama.cpp draft p_min = 0.0 (common.h L333; flag `--spec-draft-p-min`, arg.cpp L4256, non usato): la catena MTP non si ferma per probabilità.

## 6. Controlli e criteri (in quest'ordine)
**(0) Condizione cap-prefix: NON soddisfatta.** Dati in traces/mtp_cap_prefix_check.json (sha256 349866f270653c9fdced2e8a13a6b9fe94f1f0136aeb015b8c30640acb002ef2), con lo stesso contesto (stessi prompt_ids e stesso prefisso di output):
- live k3 vs k7: 351/378;
- k1 vs k7: 373/378;
- k2 vs k7: 284/298;
- k5 vs k7: 269/306;
- live k3 (v1.1, p30) vs TF cap 7: 779/799;
- agent_turns: 878/897;
- mtbench2: 311/348.

I cand.mtp dipendono quindi dal cap e dalla storia dei batch, non solo dal contesto. Le ripetizioni allo stesso cap coincidono (1181/1181).
- Per la regola: prima del ±3% si rigenera un TF a cap 3 sui 90 prompt (passo 0 dello script, `holdout_tf_cap3_v14`), e il replay di Policy va rifatto su quel TF.
- **Limite dichiarato.** Il TF processa righe singole, il live ne processa T. Anche il TF cap 3 può non coincidere col live: il controllo di validità (1) lo misura.
- Nota: le tracce v1 k* hanno 11 round con 7 token a fine output (difetto G9 delle tracce vecchie, cap 0 = nessun cap). Sono compresi nei conteggi.

**(1) Validità.** Dove il contesto live coincide con il greedy, cand.mtp live (cap 3) deve essere uguale ai primi 3 token MTP del TF (cap 3 rigenerato e primi 3 del TF cap 7).
- Output: `validity_cand_mtp_live_vs_tf.json`.
- Se non coincide al 100%, **il confronto ±3% non vale** (regola del Lead).

**(2) Coerenza ≥ 99%.** Il replay di strata_arbiter_v1.py sui candidati live registrati deve riprodurre la scelta (T, lookup) in almeno il 99% dei round (`aprime_post.json`.coherence). Altrimenti il ±3% non si legge.

**(3) ±3%.** Si confronta l'AL per dominio (code, edit), somma/somma (criterio) e media per prompt, fra il live e il **replay TF di Policy**. Riferimento: **"run file di Strata Policy, da fissare"**: percorso e sha da inserire quando esiste.
- AL live per round = min(accepted+1, committed), con committed clampato a EOS dal tracer v14.
- Si riportano anche i valori senza first_window e quelli pre-divergenza.

**(4) Greedy.** Output (a') identico a default (a) e greedy_equal_ref verso ref_holdout_tf.tsv, con first_divergence_pos per le eccezioni.

Ognuno dei controlli (1), (2), (3) si riporta separatamente. Nessun numero si ricava finché la run non esiste.

## 7. Campi registrati per round (tracer v14, cfr. traces/LOG_SCHEMA_v2.md)
- `cand.mtp`: tokens, probs, ent, probs_sampler (cap 3);
- `cand.lookup`: tokens (propose(7), completo) e match;
- `arbiter`: {impl, arm, S, S_mtp, spec_min_p, first_window, k_full, k_used, match, t_mtp, gate, choose_called, lookup, T_pre_room, room, T, q, mtp_tokens_tmtp, rounds_before, observed};
- esito del verify: accepted, committed, committed_raw, eos_clamped, target_tokens;
- `ms_measured.mtp_process`: `null` senza contesto MTP;
- per richiesta: mtp_ctx.

## 8. Licenze
- Prompt: HumanEval (MIT), MT-Bench / FastChat (Apache-2.0), edit_np (MIT), con le fonti pinnate in traces/DATASETS.md.
- Strata: MIT. llama.cpp: MIT.
- Gli output della run (token id) restano sotto traces/raw, come le run precedenti. I file del dominio edit hanno `edit_np` nel nome (§0).

## 9. Stato
- Il tracer v14 è compilato (19:33 CET) ma **non è ancora stato eseguito**: nessuno smoke test, per la regola "un solo llama" mentre agent_v12 era in corso.
- Il primo prompt della run fa da smoke test: se `aprime_holdout_v14.err` mostra errori, fermarsi.
