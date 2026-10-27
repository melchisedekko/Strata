# Scout H-LANG: drafting guidato da grammatica, sintassi o linguaggio per lo speculative decoding su codice

Data: 2026-10-26. Base: Strata `7dd5cf18e68c639a8773e096c5c79f971ea2a9f5` (MIT), clone in `/workspace/Strata`, mai modificato.
Lavoro in sola lettura: nessuna build, nessuna installazione, nessun commit. I repository esterni sono stati letti tramite clone
shallow/sparse in `/tmp`, fuori dalla cartella pubblica.

Legenda: **[V]** = verificato aprendo davvero il file o la pagina (con file:righe o URL); **[P]** = plausibile, cioè una
deduzione o un'ipotesi non verificata.
Stato di ogni voce: *implementato in Strata* / *implementato altrove* / *plausibile*.
Regola sui numeri: gli speedup dei paper sono riportati solo come "riportato dal paper X, su modello/hardware Y" e **non**
valgono per Strata.
Questo file non contiene token, testo delle tracce o dati di dataset con licenza non pubblicabile.

---

## 0. Vincolo di correttezza: output greedy-identico

- [V] In Strata il drafter propone e il verify decide.
  - `include/strata/spec/draft_source.hpp` L3-4: «the verify window checks the proposal, so a source can only change the
    speed, never the output».
  - Anche `draft_policy.cpp` L144-145: «verification keeps the output; only the one round's speed is at stake».
- [P] Ne segue la regola di ammissibilità per H-LANG: qualunque fonte sintattica o grammaticale è ammessa **solo come
  proposta di draft** da mettere nella finestra di verify. I token "forzati" con jump-forward / fast-forward e committati
  **senza** che il target li verifichi non sono ammissibili. Il modello non vincolato può comunque scegliere un token
  diverso: un'altra tokenizzazione della stessa stringa, un errore di sintassi voluto, la fine del blocco.
- [V] Gli stessi engine dicono che i token forzati non coincidono per forza con la scelta del modello.
  - XGrammar `python/xgrammar/matcher.py` L426-441 (commit `e085851a`), `find_jump_forward_tokens`: «This tokenization may
    differ from the model tokenizer's encoding».
  - Il blog LMSYS sul compressed FSM, sezione "Tokenization Boundary Handling", dice che tokenizzazioni diverse della parte
    saltata «may lead to different logit distributions» e introduce la re-tokenizzazione:
    https://lmsys.org/blog/2024-02-05-compressed-fsm/
- [V] Il modo corretto in greedy-identico, con una grammatica, è "draft e poi verifica".
  - In llama.cpp `common/sampling.cpp` L690-722 (`common_sampler_sample_and_accept_n`, commit `d327bf1f`) un draft è accettato
    solo finché `draft[i] == id` campionato dal target. Lì però la grammatica vincola anche il target (`grammar_first`), mentre
    Strata non ha un decoder di grammatica (`serve/structured.py` L3, [V]).
  - [P] Quindi in Strata una grammatica o un parser servirebbero **solo** a generare o a potare draft, mai a mascherare il
    target.

---

## 1. Stato dell'arte

### 1.1 Drafting sintattico o grammaticale (parser, AST, tree-sitter)

| Voce | Link | Licenza | Cosa fa | Greedy-identico? | Stato |
|---|---|---|---|---|---|
| DOMINO, "Guiding LLMs The Right Way: Fast, Non-Invasive Constrained Generation" | arXiv:2403.06988, §3.6 | paper CC BY 4.0 [V]; repo `github.com/eth-sri/domino` **vuoto** [V] (API GitHub: «This repository is empty», nessuna licenza) | Modello di speculazione **count-based** condizionato sullo stato scanner/parser (α, β): P(l \| α, β) = conteggio delle scelte del LLM in quello stato. Si propongono più token se P è abbastanza alta. Il paper dice che è indipendente dallo spec decoding classico e combinabile con esso [V, testo §3.6] | [P] Sì, se i token vanno al verify. Nel paper la generazione è vincolata dalla grammatica, quindi il target è mascherato, a differenza di Strata | implementato altrove (codice non pubblicato) |
| Speculative Decoding for Verilog | arXiv:2503.14153 | non verificata | Allinea gli stop di decodifica a token sintatticamente significativi. Serve training (heads/draft) [V, abstract] | [P] non è un drafter senza training; poco trasferibile | implementato altrove. Riportato dal paper: fino a 5.05× su generazione Verilog (RTLLM), con il loro modello/setup |
| SynCode | arXiv:2403.01632; repo `structuredllm/syncode` (redirect da `uiuc-focal-lab/syncode`) | MIT [V, API GitHub] | Decodifica vincolata da CFG con "DFA mask store" offline; grammatiche per Python e Go [V, abstract] | [P] è un masking, non un drafter; utile come **oracolo** di "token ammessi" | implementato altrove |
| Copy-as-Decode | arXiv:2604.18170 | non verificata | FSM token-level e copia di span via parallel prefill, «program-enforced acceptance replacing probabilistic verification» [V, abstract] | **No**: accetta senza verify | implementato altrove (studio di upper bound). Riportato dal paper: kernel 6.8×–303× su Qwen2.5-1.5B/7B, A100 |
| CDSL, Constrained Decoding with Speculative Lookaheads | arXiv:2412.10418 | non verificata | Draft LLM e verify con target più reward di vincolo [V, abstract] | [P] no: l'obiettivo è il soddisfacimento di vincoli, non l'identità | implementato altrove; non pertinente al drafting sintattico |
| LinguaSpec (ACL Findings 2026) | https://aclanthology.org/2026.findings-acl.1065/ | non verificata | Prior linguistici e POS per regolare la profondità del draft e il «verification rigor» (POS-Adaptive Deferred Verification) [V, abstract] | [P] la parte di verifica rilassata **non** è greedy-identica; l'idea "profondità per categoria" è riusabile | implementato altrove |
| tree-sitter | `github.com/tree-sitter/tree-sitter` @ `dfe770858e3cfd8e8b29a79ea17da390a6f60319`, `lib/include/tree_sitter/api.h` | MIT [V] | Parser incrementale in C senza dipendenze (README L7-12 [V]). API utili per i token forzati: `ts_parser_parse` L325, `ts_tree_edit` L464, `ts_node_next_parse_state` L617, `ts_language_next_state` L1341, `ts_lookahead_iterator_new` L1371, `ts_lookahead_iterator_next` L1404 [V] | strumento, non un drafter | plausibile come base per un drafter o per l'oracolo offline |

- [P] Non ho trovato un drafter **lossless** pubblico basato su tree-sitter per lo spec decoding su codice.
- Ho visto un progetto personale "SASD" (tree-sitter) solo nei risultati di ricerca, senza aprire codice o licenza:
  **non verificato**.

### 1.2 Modelli n-gram/suffix per linguaggio o dominio

| Voce | Link (file:righe @ commit) | Licenza | Condizionamento per linguaggio? | Stato |
|---|---|---|---|---|
| SuffixDecoding | arXiv:2411.04975 [V, abstract: suffix tree su prompt e output precedenti, speculazione adattiva]; codice `snowflakedb/ArcticInference` @ `aca5d9a8a62474035c15d114d40a01abc8c94b51`, `arctic_inference/suffix_decoding/cache.py` (classe `SuffixDecodingCache` L59, `start_request` L120, `speculate` L235) | Apache-2.0 [V] | [V] Nessun riferimento a linguaggio, dominio o task in `cache.py` (rg). L'albero globale è condiviso tra le richieste | implementato altrove. Riportato dal paper: fino a 5.3× su benchmark agentici (SWE-Bench, Text-to-SQL), con il loro setup |
| vLLM suffix | `vllm-project/vllm` @ `9e3db48873b87a3c232f16991675d33abb49b72b`: `vllm/v1/spec_decode/suffix_decoding.py` L9-13 (usa l'implementazione ArcticInference); config `vllm/config/speculative.py` L537-556 (`suffix_decoding_max_tree_depth`, `max_cached_requests`, `max_spec_factor`, `min_token_prob`) | Apache-2.0 [V] | [V] Nessun parametro per linguaggio nella config | implementato altrove |
| vLLM ngram (prompt lookup) | stesso commit: `vllm/v1/spec_decode/ngram_proposer.py` (classe L12, numba; `_find_longest_matched_ngram_and_propose_tokens` L210); config `prompt_lookup_max/min` L502-508 | Apache-2.0 [V] | [V] no | implementato altrove |
| vLLM: grammatica e spec | `vllm/v1/structured_output/__init__.py` L362-380 `validate_tokens`: «Return the longest unconstrained or grammar-valid prefix of `spec_tokens`»; `grammar_bitmask` L382-386 riceve `scheduled_spec_decode_tokens` | Apache-2.0 [V] | n/a | implementato altrove. È un **taglio** dei draft per grammatica: il target resta vincolato |
| SGLang ngram | `sgl-project/sglang` @ `656331295619a4d0267b40b7da0b5cd5b549fcbc`: `python/sglang/srt/speculative/ngram_worker.py` L114-164 (`NgramCorpus`, `add_external_corpus` L154, corpus esterno da `speculative_ngram_external_corpus_path` L124-141); `external_corpus_manager.py` L1-5 «Manages external SAM corpora for ngram speculative decoding» | Apache-2.0 [V] | [V] Corpora esterni con **nome** (add/remove/list). [P] Un corpus per linguaggio o dominio sarebbe possibile. **Non ho verificato** se il corpus si scelga per richiesta o se tutti i corpora siano interrogati insieme | implementato altrove |
| REST | arXiv:2311.08252 [V, abstract: retrieval da un datastore per i draft]; `FasterDecoding/REST` | Apache-2.0 [V] | [P] Il datastore è per dominio (codice o chat) per costruzione; non ho aperto il codice | implementato altrove. Riportato dal paper: 1.62×–2.36× su modelli 7B/13B, single batch |
| Prompt Lookup Decoding | `apoorvumang/prompt-lookup-decoding` | **nessuna licenza dichiarata** [V, API GitHub `license: null`] | no | implementato altrove; equivalente a SuffixDrafter |
| Lookahead Decoding | arXiv:2402.02057 [V titolo]; `hao-ai-lab/LookaheadDecoding` | Apache-2.0 [V] | [P] no | implementato altrove |
| llama.cpp ngram-cache, lookup statico e dinamico | `/workspace/llama.cpp` @ `d327bf1f0780f87b8c01b367b61853b0c291d7c4`: `common/ngram-cache.h` L9-11, L73, L96; `common/arg.cpp` L1635-1648 (`-lcs/--lookup-cache-static` «not updated by generation», `-lcd`); `common/speculative.cpp` L75-85 tipi, L2273-2310 ngram-cache; `examples/lookup` (lookup-create/merge/stats) | MIT [V] | [V] Nessun condizionamento per linguaggio. [P] Una **cache statica per linguaggio** costruita offline con `lookup-create` è l'analogo più diretto di "n-gram per linguaggio" | implementato altrove; per linguaggio = plausibile |
| Strata SuffixDrafter | `include/strata/spec/suffix_drafter.hpp` L1-10, L21-39; `src/spec/suffix_drafter.cpp` L18-19, L33-36, L51-96 | MIT | [V] Nessuna logica di linguaggio; indice per richiesta (prompt e output) | implementato in Strata |

- [V] Nel codice letto, nessuno dei sistemi n-gram/suffix ha un condizionamento esplicito per linguaggio di programmazione.
  L'unico meccanismo vicino è il corpus esterno con nome di SGLang, insieme alla cache statica di llama.cpp.

### 1.3 Engine di constrained decoding riusabili e jump-forward / fast-forward

| Voce | Link (file:righe @ commit) | Licenza | Primitive utili come drafter | Ammissibile in greedy-identico? | HIP/ROCm |
|---|---|---|---|---|---|
| XGrammar | arXiv:2411.15100 [V titolo]; `mlc-ai/xgrammar` @ `e085851aec8f417924be5f460d1e038cac0e3bd5`, `python/xgrammar/matcher.py`: `traverse_draft_tree` L366-411 (bitmask per ogni nodo di un albero di draft), `find_jump_forward_string` L412-424 («can become the output of the LLM without requiring LLM decoding»), `find_jump_forward_tokens` L426-441; C++ `cpp/grammar_matcher.cc` L2183 | Apache-2.0 [V] | La stringa o i token di jump-forward vanno usati **come draft** | Solo se verificati (§0) | [P] Il matcher gira su CPU. Non ho verificato i kernel di bitmask su ROCm, ma un drafter non ne ha bisogno |
| llguidance | `guidance-ai/llguidance` @ `4a671ad283eaeee11e02966b66c896aafec20feb`: `parser/src/tokenparser.rs` L935-955 (`compute_ff_tokens`, «tokens to fast-forward, forced by the current parser state»), `parser/src/matcher.rs` L230-240; `toktrie/src/lib.rs` L38-46 (`InferenceCapabilities.ff_tokens`, `conditional_ff_tokens`); `sample_parser/src/sample_parser.rs` L330 «In production, ff_tokens are appended to the output without LLM sampling» | MIT [V] | `compute_ff_tokens` come draft | Solo come draft (il default descritto è senza sampling, quindi non ammissibile così com'è) | [P] Rust, solo CPU |
| Outlines | arXiv:2307.09702 [V titolo]; `dottxt-ai/outlines` @ `c52af8472c6fe8a607a733ec11b709476af77a96` | Apache-2.0 [V] | FSM o regex. Il jump-forward di SGLang è nato sul backend Outlines (`sglang/srt/constrained/outlines_backend.py` L83-111 @ `656331…` [V]) | idem | [P] CPU |
| SGLang jump-forward | blog https://lmsys.org/blog/2024-02-05-compressed-fsm/ [V]; API `base_grammar_backend.py` L119-145 (`try_jump_forward`, `jump_forward_str_state`, `jump_and_retokenize`) @ `656331…` [V] | Apache-2.0 | Il jump-forward e la re-tokenizzazione aggiungono la stringa senza decodificarla | No, così com'è | n/a. Riportato dal blog: fino a 2× di latenza e 2.5× di throughput su JSON decoding rispetto a guidance+llama.cpp e outlines+vLLM |
| llama.cpp GBNF | `/workspace/llama.cpp/grammars/README.md` L1-11 [V]; grammatiche `grammars/*.gbnf` (c'è una `c.gbnf` giocattolo [V], non una grammatica completa di C) | MIT | Masking del target; `common/llguidance.cpp` esiste [V] | Il verify con grammatica (sampling.cpp L690-722) vincola il target, quindi non vale per Strata | n/a |

- [P] Nessun engine CFG copre linguaggi di programmazione reali (Python, C++, …) con fedeltà da compilatore. Le grammatiche
  GBNF, Lark (SynCode) ed EBNF (XGrammar) sono approssimazioni. Un falso "forzato" però costa solo velocità, non output,
  perché il verify scarta il draft.

### 1.4 Rilevamento del linguaggio a basso costo

| Voce | Link | Licenza | Note | Stato |
|---|---|---|---|---|
| Info string dei fence ```` ```lang ```` | CommonMark (convenzione) | — | È già estratta **offline** da `strata-policy/replay/hca.py` L77-87 `fences()` (indice del token che chiude il terzo backtick, info string troncata) [V]. Il motore C++ **non** la estrae: in `serve/frontend.py` L1073-1074 `_track` riconosce ``` e ~~~ ma conserva solo il carattere del fence, non il linguaggio [V] | parziale in Strata (offline e serve Python) |
| Estensioni, shebang, modeline | linguist `docs/how-linguist-works.md` L8-16 @ `73ee9a3b277f398c37ca4ab0dea0193849de6460` (strategie in ordine: modeline, shebang, estensione, …, heuristics, …) | MIT [V] | Ruby. [P] Utile solo se il prompt contiene nomi di file | implementato altrove |
| guesslang | `yoeo/guesslang` @ `42ec63776777e1bdce2d72f51710c6634e36e00c`, README L21, L37, L71 | MIT [V] | TensorFlow; il README dichiara 54 linguaggi e accuratezza >90% (dichiarazione del README) | implementato altrove; dipendenza pesante |
| Magika | arXiv:2409.13768 [V titolo]; `google/magika` @ `8d3d3b9b9452a65a6aa7752e061a67bf4a6b3c9b`, README L16, L33-39 | Apache-2.0 [V] | Content-type detection (200+ tipi, CLI Rust, circa 5 ms per file su CPU secondo il README) | implementato altrove |
| hyperpolyglot | `monkslc/hyperpolyglot` | Apache-2.0 [V] | Port Rust di linguist (non ho letto il codice) | implementato altrove [P] |
| tree-sitter come rilevatore | — | MIT | [P] Si parsa con N grammatiche e si sceglie quella con meno nodi ERROR. È più costoso | plausibile |

- [P] Per Strata il rilevamento più economico, e coerente con H-CA, è l'info string del fence vista nel prompt e nell'output
  già prodotto. Le estensioni dei file servono come fallback. guesslang e Magika sono dipendenze esterne, solo per l'offline.

---

## 2. Cosa esiste già in Strata a `7dd5cf1` (rg/sed, solo lettura)

- [V] **Fence / H-CA.**
  - Nel motore C++ (`src/`, `include/`) non c'è alcun riconoscimento di fence o di linguaggio. Ho cercato con rg
    `tree-sitter|guesslang|linguist|gbnf|xgrammar|llguidance|outlines`: nessuna occorrenza pertinente in `src/` e `include/`.
  - I fence esistono in:
    - `serve/frontend.py` L936-942 e L1047-1091 (`_track`, `_opener_ok`, `_in_code`, per il parsing delle tool call);
    - `serve/web/app.js` L956-957 (fence per gli allegati, lato UI);
    - offline in `strata-policy/replay/hca.py` (L30 `FENCE`, L77-87 `fences`, L121-122 `in_code` e `prompt_fence`, L190 feature
      bit `in_code<<3 | prompt_fence<<2 | lk_rate<<1 | mtp_p`, L224-230 conteggi per info string).
- [V] **lk_rate.**
  - Non esiste come variabile del motore.
  - Il tasso di lookup del motore è `DraftPolicy::lookup_rate(match)` (`draft_policy.cpp` L36-39), basato sui contatori
    `ok_/bad_` per **bucket di match** (`bucket()` L32-34: `match <6 / <12 / <24 / oltre`).
  - `lk_rate` è una feature **offline** di `hca.py` (finestra mobile, L161 e seguenti).
- [V] **set_context / bucket.**
  - `set_context(pos)` (`draft_policy.cpp` L76-96) sceglie la riga di costo per lunghezza del contesto (`kCtxBuckets=3`,
    `draft_policy.hpp` L27).
  - È attivo solo con `set_robust` (`STRATA_SPEC_COST`).
  - È chiamato in `generate.cpp` L16537 (CLI) e L14882 (serve).
  - Nessun bucket per linguaggio o dominio.
- [V] **SuffixDrafter.**
  - CLI: `generate.cpp` L16428 `SuffixDrafter sfx(max(1,o.suffix_draft), 64, max_context+4096)`.
  - Gate non-chain L16554-16563 (CLI) e L14894-14903 (serve): `sfx.propose(o.spec - 1 | S - 1)`, condizione
    `sbuf[0] == drafts[0]`, poi `policy.choose(T, k, sfx_match)`.
- [V] **Fonti extra.**
  - `DraftSource` (`draft_source.hpp` L21-34), `extra_draft_sources()` L55, `propose_from_sources` L59-60.
  - Implementazione in `src/spec/draft_source.cpp` L13-34: vince il match più lungo `>= min_match`; a parità vince la fonte
    precedente; `*source` = indice.
  - Usate **solo** nel percorso `--lookup-chain` (`generate.cpp` L16570-16582: dopo una finestra MTP, poi `policy.chain`).
  - Il gate principale (lookup **al posto** di MTP) non le interroga.
- [V] **Commento rilevante.** `draft_policy.cpp` L182-183: «code and thinking text are over-confident» (calibrazione MTP).
- [V] **Manopole già esposte.** Riferimento incrociato `scout_patch_support.md` §11: `--spec`, `--mtp-max-t`, cap del lookup
  `S-1`, `--suffix-draft` = min_match, `--spec-min-p` per richiesta in serve, `--lookup-chain`, `STRATA_SPEC_COST`.
  Nessuna è condizionata dal linguaggio.

---

## 3. (1) Config per linguaggio (T, min_p, cap del lookup per round): cosa servirebbe

- [P] **Chiave di linguaggio.**
  - Va ricavata a runtime dall'info string dell'ultimo fence aperto, nel prompt o nell'output già committato.
  - In C++ servirebbe un piccolo tracker di fence sui pezzi detokenizzati, cioè l'equivalente di `hca.py fences()` e di
    `frontend.py _track`, ma con la cattura dell'info string. In serve si può anche calcolare in Python (frontend) e passare
    per richiesta, come già succede per `--spec-min-p` per richiesta (`scout_patch_support.md` §11).
- [P] **Profilo per linguaggio.**
  - Una tabella `lang -> {T_mtp max, min_p, cap del lookup per round, min_match}` applicata a ogni round nei punti già
    esistenti:
    - T: `generate.cpp` L16536 `T=S_mtp`, rami L16538-16543;
    - cap del lookup: argomento `o.spec - 1` di `sfx.propose` a L16557 / `S - 1` a L14897;
    - min_p: dove è già letto per richiesta.
  - Il cap per round deve rispettare `k <= max_t_ - 1 <= kMaxT - 1` (`draft_policy.hpp` L25, `choose` L131).
- [P] **Statistiche per linguaggio in DraftPolicy.**
  - Oggi `ok_/bad_` sono per bucket di match (hpp L91) e `cost_` per bucket di contesto (hpp L88).
  - Un indice di linguaggio su `ok_/bad_` (o un `DraftPolicy` per linguaggio) è l'analogo di `set_context`.
  - Il costo `cost_` dipende da T e dal contesto, non dal linguaggio, quindi va lasciato **condiviso** [P].
- [P] **Rischi.** Le statistiche si frammentano (meno osservazioni per cella). Il cambio di linguaggio a metà output
  (prosa → codice) richiede un reset o un decadimento: c'è già `kDecay` (cpp L17).

## 4. (2) Drafter sintattico come terza fonte o come estensione del lookup

- [P] **Opzione "estensione del lookup".**
  - Una nuova `DraftSource` registrata con `extra_draft_sources()`.
  - Costo minimo di integrazione, ma oggi agisce solo in `--lookup-chain`, dopo la finestra MTP.
  - L'arbitro è il match più lungo (`draft_source.cpp` L22): una fonte sintattica dovrebbe esprimere un `match` comparabile
    con quello del suffix, e non lo è.
- [P] **Opzione "terza fonte nel gate".** Vedi §5. Permette a una fonte sintattica di sostituire MTP nel round, come fa
  oggi il lookup.
- [P] **Contenuto della fonte**, in ordine di costo crescente:
  - (a) tabella count-based alla DOMINO (§1.1) indicizzata da uno stato sintattico leggero (dentro una stringa, un
    commento, una lista di argomenti, l'indentazione…) calcolato da un tokenizer lessicale per linguaggio;
  - (b) stato del parser tree-sitter con `ts_lookahead_iterator_*`, per l'insieme dei simboli ammessi;
  - (c) jump-forward di una grammatica XGrammar o llguidance usato come draft.
  - Tutte e tre sono solo CPU, quindi senza vincoli HIP/ROCm per il drafting [P]. Il verify resta quello esistente.

## 5. (A) Terza fonte in `DraftPolicy::choose` e nel loop di `generate.cpp`: punti da toccare (solo testo, nessuna patch)

**Firme da estendere** [V per le righe, P per le modifiche]:
- `draft_policy.hpp` L31-34 `struct Pick { bool lookup; int t; }`: diventerebbe una fonte enumerata (`MTP | LOOKUP | SYN`).
  Oggi il booleano `lookup` è usato in L16561 / L14901 (`if (pk.lookup) { T = pk.t; from_sfx = true; }`).
- `draft_policy.hpp` L36 `Pick choose(int t_mtp, int lookup_k, int match) const`: aggiungere `(int syn_k, int syn_conf)`
  oppure una lista di candidati `(fonte, k, chiave del bucket)`.
- `draft_policy.hpp` L38 `void observe(bool lookup, int t, int accepted, int match, double round_ms)`: il booleano diventa
  la fonte.
- `draft_policy.hpp` L48 `lookup_rate(int match)`: serve un `rate(fonte, chiave)`.

**Stato interno e contatori per fonte** [V righe]:
- `ok_/bad_` (hpp L91, `kBuckets=4` L26) sono solo del lookup e sono aggiornati in `observe` (cpp L164-167).
- La terza fonte richiede contatori propri `syn_ok_/syn_bad_[bucket]`, con il proprio prior (oggi `kPriorQ`, `kPriorN`,
  cpp L20-21) e la propria funzione di bucket (cpp L32-34 è basata sul match del suffix e non ha senso per una fonte
  sintattica [P]).
- `mtp_tok_/mtp_n_` (hpp L90) restano invariati.
- I contatori della catena `cok_/cbad_` (hpp L92) non distinguono la fonte, anche se `propose_from_sources` restituisce già
  `*source` (`draft_source.cpp` L31; `csrc` in `generate.cpp` L16572) [V]. Andrebbero separati se la fonte sintattica
  entrasse anche in catena.

**Logica di `choose`** (cpp L123-152) [V righe]:
- Oggi: `base = mtp_tokens(t)/cost_ms(t)`, poi il loop k fino a `min(lookup_k, max_t_-1)` (L131) con il valore atteso
  geometrico `e += q^k` e `r = e/cost_ms(k+1)`, scelta se `best > base*(1+margin_)` (L138).
- Una terza fonte ripete lo stesso loop con il proprio `q`, e si prende l'argmax tra le tre.
- [P] `margin_` (default nel costruttore, hpp L29) è un'isteresi a favore di MTP. Va deciso se usarne uno condiviso o uno
  per fonte: la regola la fissa il Lead.
- **Cost table**: `cost_[bk_][T]` (hpp L88) è indicizzata dalla dimensione della finestra, non dalla fonte, quindi si
  condivide. [P] Il costo di proposta della fonte sintattica (tempo CPU del parser) è fuori dal verify. Oggi `round_ms`
  include già il tempo di draft (commento hpp L37: «verify + commit + draft»), quindi entra nell'EMA. Però si mescola tra
  fonti con costi di proposta diversi: è un punto da decidere.
- **Stale e probe**: L142 (re-misura di `t_full` stale se `q >= 0.85`) e L147 (probe `cost_n_ < kProbes || stale`) sono
  scritti per il lookup. Con una terza fonte vanno resi per fonte, oppure vanno limitati, per non far esplodere le probe.
  `kProbes` (cpp L22) e `kStaleRounds` (cpp L25) sono costanti.
- **Limite**: `kMaxT = 8` (hpp L25), quindi `k <= 7` per qualunque fonte. Gli array `cost_`, `mtp_tok_` e `last_` sono
  dimensionati `kMaxT+1`.

**Loop di generate** [V righe]:
- Gate CLI L16554-16563.
  - Oggi: `sfx.propose` e la condizione `!use_mtp || sbuf[0] == drafts[0]`, cioè il lookup è ammesso solo se il primo draft
    coincide con quello di MTP.
  - Una terza fonte richiede un `sbuf2` (accanto a `sbuf`, allocato vicino a L16454-16456), la propria condizione di accordo
    e una sola chiamata `choose` con tre candidati.
  - Gate serve speculare a L14894-14903.
- Riempimento della finestra L16591-16599: `d = from_sfx ? sbuf[i-1] : drafts[i-1]` va generalizzato a un puntatore al
  buffer della fonte scelta. La catena (L16596 `if (i >= T_mtp) d = cbuf[...]`) parte solo se `!from_sfx` (L16571).
- Osservazione L16713-16715 (CLI) e L15190-15196 (serve):
  - `observe_probs` solo se `!from_sfx`: andrebbe esteso a "solo se la fonte è MTP";
  - `policy.observe(from_sfx, T, a, sfx_match, round_ms)`: passare la fonte e la sua chiave di bucket;
  - `observe_chain` resta invariato.
- Trace L16704-16707: la colonna `from_sfx ? 1 : 0` diventerebbe l'id della fonte. [P] Va aggiornato anche `log_format.md`
  (campo `source`, mappatura in L94).
- [P] **Contatori di diagnostica.** Oggi ci sono `sfx_windows/sfx_drafts/sfx_ok` (vicino a L16454-16456); servirebbero gli
  equivalenti per la fonte sintattica.

## 6. (B) Tetto offline: "tra i token che MTP e lookup NON fanno accettare, quanti sono sintatticamente forzati"

**Definizione operativa** [P], senza numeri:
1. Per ogni richiesta del dominio codice si prende la sequenza greedy `y` (teacher-forced) e si ripercorrono i round come nel
   replay esistente: a ogni round la posizione corrente `i`, i candidati `cand.mtp.tokens` e `cand.lookup.tokens`, e la loro
   accettazione `acc.mtp` / `acc.lookup` (LCP con `y`).
2. Insieme **N** = posizioni di `y` che **non** sono coperte né dall'accettazione MTP né da quella lookup, nell'oracolo per
   round che sceglie la fonte con più token accettati. Sono quindi esclusi i token che MTP già prende.
3. Una posizione `j ∈ N` è **sintatticamente forzata** se, dato il testo `detok(prompt + y[:j])` e il linguaggio `L` del
   blocco (dall'info string del fence aperto; se manca, la posizione è "linguaggio ignoto" e non si conta), l'analizzatore
   sintattico di `L` ammette per il prossimo token un'**unica** continuazione compatibile con il vocabolario, e quella
   continuazione è proprio `y[j]`.
   - Variante debole: insieme ammesso piccolo con `y[j]` tra i membri. Variante di sequenza: la lunghezza del run forzato
     che parte da `j`, perché un drafter propone fino a `k <= 7` token.
4. Il tetto è il rapporto `|forzati| / |N|`, per linguaggio e complessivo. È solo descrittivo: la regola GO la fissa il Lead.
5. Fuori dai blocchi di codice (`in_code` falso) le posizioni sono contate a parte. Non c'è grammatica: al massimo l'analisi
   di fence e markdown.

**Campi delle tracce necessari** (verificati con rg/lettura delle sole **chiavi** di `traces/v1.1/tf_d7_p30.jsonl` e
`holdout_code_tf_d7.jsonl`, nessun valore letto; tracce edit **non** aperte) [V]:
- riga `request`: `req_id`, `domain`, `split`, `prompt_ids`, `ref_tokens`, `dmax`, `lookup_max_match`;
- riga `round`: `r`, `pos`, `gen_index`, `source`, `T`, `cand.mtp{tokens,probs,ent,probs_sampler}`, `cand.lookup`,
  `acc.mtp`, `acc.lookup`, `accepted`, `committed`, `domain`;
- riga `request_end`: `output_ids`;
- schema documentato in `strata-plus/log_format.md` (L23 domain, L29/L48 prompt_ids, L53-59 riga round, L81-86 cand e
  committed, L123 `round.acc.{mtp,lookup,pool}`, L160 `output_ids`) e nel replay `strata-policy/replay/SCHEMA.md`
  (`mtp_tok/mtp_acc`, `lk_tok/lk_acc`);
- [V] Nelle tracce **non** c'è un campo di linguaggio né di testo. Il linguaggio va ricavato detokenizzando con il vocabolario
  del GGUF, come fa `hca.py` (`fences()` L77-87, `load()` da L89).
- [V] Le tracce v1.1 sono **proxy CPU** (modello 2B con MTP, vedi `hca.py` e `ceiling_third_source.py` L6-7), non il target
  AMD. Il tetto misurato lì vale per il proxy.

**Strumento che lo calcolerebbe** [P]:
- uno script Python offline accanto a `strata-policy/replay/` che riusa il loader di `hca.py` e quello di
  `ceiling_third_source.py` (che esiste già, [V], come oracolo a più fonti);
- per l'analisi sintattica: **tree-sitter** (MIT, [V]) con le grammatiche per linguaggio, tramite `py-tree-sitter` (MIT, [V])
  e `ts_lookahead_iterator_*` per l'insieme dei simboli ammessi (api.h L1371/L1404 [V]);
- alternative: XGrammar (Apache-2.0) o llguidance (MIT) con una grammatica per linguaggio, che danno direttamente i token
  forzati (`find_jump_forward_tokens`, `compute_ff_tokens`) allineati al vocabolario, oppure SynCode (MIT) per Python e Go;
- [P] Difficoltà nota: tree-sitter lavora a livello di simbolo lessicale, non di token BPE. Passare da "simbolo forzato" a
  "token forzato" richiede di confrontare la stringa del token con i lessemi ammessi. Gli engine grammaticali lo fanno
  nativamente, tree-sitter no.
- Vincolo di pubblicazione: lo script e il suo output aggregato non devono contenere token né testo delle tracce. Le tracce
  di edit da dataset con licenza non pubblicabile vanno escluse dall'output pubblico.

---

## 7. Cose non verificate

- Il codice e la licenza di DOMINO (repo vuoto), di LinguaSpec, di Copy-as-Decode, di CDSL e del paper Verilog: ho letto
  solo gli abstract.
- La riga lmdeploy `guided_spec_helper.py:124-215 @67c18b90`: l'ho vista solo citata in una issue di terzi, non l'ho aperta.
- La PR SGLang #24082 (spec decoding + grammar in disagg): l'ho vista solo nei risultati di ricerca.
- Il progetto "SASD" (tree-sitter): visto solo nei risultati di ricerca.
- SGLang: non ho verificato se i corpora esterni si scelgano per richiesta.
- REST: non ho aperto il codice per vedere come si costruisce il datastore.
- I kernel di bitmask XGrammar e llguidance su ROCm: non verificati (e non necessari per un drafter CPU).
- La qualità delle grammatiche dei linguaggi reali in GBNF, Lark ed EBNF: non valutata.
- hyperpolyglot: ho visto solo la licenza.
- Lo sha256 di `draft_policy.cpp` a `7dd5cf1` è ricalcolato in questa sessione:
  `890649e3c85891acd8c3e7d6de5908591bc81ef92732ecbe6547008efd61224a` [V].

## 8. Proposta di primo passo offline (senza numeri)

1. Calcolare il tetto della §6 sul solo dominio codice delle tracce proxy esistenti:
   - linguaggio dal fence;
   - forzatura con tree-sitter (variante simbolo) e, come controllo incrociato, con una grammatica XGrammar o llguidance
     (variante token);
   - esclusione delle posizioni già coperte da MTP e lookup;
   - output solo aggregato, per linguaggio.
2. Nello stesso replay, misurare per linguaggio il tasso di accettazione di MTP e lookup che le tracce già contengono, per
   capire se una config per linguaggio (§3) ha senso anche senza una fonte nuova.
3. Se il Lead dà GO sul tetto, prototipare offline una fonte count-based alla DOMINO (stato sintattico leggero → token
   successivi) dentro l'oracolo a tre fonti già esistente (`ceiling_third_source.py`), come terza fonte al posto di
   `ngram_mod`/`suffix`.
4. Solo dopo, scrivere il design testuale delle modifiche della §5 (Pick con fonte, contatori per fonte, gate a tre vie)
   come proposta da far revisionare, senza toccare `/workspace/Strata`.
