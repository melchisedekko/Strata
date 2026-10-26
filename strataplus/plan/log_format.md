# Strata+ — formato di log per round `strataplus.v1.1` (allineato a piano.md §6)

Stato: **v1.1** (2026-10-25). Strata Lead ha **approvato le divergenze D1–D14** (sezione 4). Rispetto a v1 cambia
solo lo stato dei campi: **obbligatori per il replay D1, D2 oppure D13, D3, D4**; gli altri campi `[+]` restano
facoltativi. Il valore del campo `schema` diventa `"strataplus.v1.1"`; un lettore v1.1 accetta anche file
`"strataplus.v1"` che contengano i campi obbligatori (le tracce Bench attuali in `traces/` sono `strataplus.v1` e
li contengono). Autore: Strata Policy.
Il formato di riferimento resta quello del piano §6; le differenze sono elencate nella sezione
«Divergenze da piano §6» (D1–D14, ora approvate).
Repo di riferimento: github.com/Niko1221/Strata @ `7dd5cf18e68c639a8773e096c5c79f971ea2a9f5`.

## 1. Struttura del file

- JSONL, UTF-8, una riga = un oggetto. Un file per run (`<run_id>.jsonl`), oppure uno per dominio.
- Per ogni richiesta: **una riga `request`**, poi **una riga `round`** per ogni round di verifica (in ordine).
- Ordine delle richieste nel file = ordine di servizio (serve per H2: il pool vede solo le richieste precedenti).
- `engine` ∈ `strata | llamacpp | sim`.

### 1.1 Riga `request`

```json
{"type":"request","schema":"strataplus.v1.1","run_id":"…","engine":"llamacpp","engine_rev":"<git sha>",
 "model":"Qwen3.5-2B-Q4_K_M","flags":"…","dataset":"humaneval","domain":"code|chat|edit","req_id":"…",
 "session_id":"…|null","turn":0,"prompt_sha256":"…","prompt_tokens":0,"output_sha256":"…","output_tokens":0,
 "ref_output_sha256":"…",
 "data_kind":"live|teacher_forced|synthetic",          // [+] OBBLIGATORIO per noi: vedi D1
 "dmax":7,                                              // [+] profondità MTP registrata (Dmax), vedi D3
 "ref_tokens":[…],                                      // [+] y (output greedy di riferimento, id token), vedi D2
 "prompt_ids":[…]                                       // [+] facoltativo: id del prompt (serve a E1/H2 per rifare il lookup)
}
```

| Campo | Tipo | Obbl. | Significato |
|---|---|---|---|
| `type` | `"request"` | sì | |
| `schema` | `"strataplus.v1.1"` (accettato anche `"strataplus.v1"`) | sì | |
| `run_id`, `req_id` | string | sì | `req_id` univoco nel run |
| `engine`, `engine_rev` | string | sì | sha git del motore (Strata: commit; llama.cpp: commit) |
| `model`, `flags` | string | sì | riga di comando completa in `flags` (incl. env `STRATA_*` rilevanti) |
| `dataset`, `domain` | string | sì | `domain` ∈ `code|chat|edit` (estendibile: `agent`) |
| `session_id`, `turn` | string/null, int | sì | sessioni multi-turn (H2); `null` per richieste indipendenti |
| `prompt_sha256`, `prompt_tokens` | string, int | sì | |
| `output_sha256`, `output_tokens` | string, int | sì | output di questo run |
| `ref_output_sha256` | string | sì | sha di y (run senza speculazione); M5: deve coincidere con `output_sha256` |
| `data_kind` [+] | enum | **sì (per noi)** | `live` = run reale con policy; `teacher_forced` = una riga per posizione di y; `synthetic` = generato, **nessun numero da queste righe è una misura** |
| `dmax` [+] | int | sì se `cand.mtp` presente | lunghezza di `cand.mtp.tokens` (Dmax) |
| `ref_tokens` [+] | int[] | consigliato | y; senza, l'accettazione controfattuale di candidati non loggati è impossibile |
| `prompt_ids` [+] | int[] | facoltativo | per ricostruire lookup/pool offline con il `SuffixDrafter` reale |

### 1.2 Riga `round`

```json
{"type":"round","run_id":"…","req_id":"…","r":17,"pos":412,"ctx_len":1530,"ctx_bucket":0,
 "source":"none|mtp|lookup|chain|pool","k_proposed":3,"T":4,"proposal":[1,2,3],
 "cand":{"mtp":{"tokens":[…Dmax],"probs":[…Dmax],"ent":[…Dmax]},   // ent: [+] facoltativo, vedi D11
         "lookup":{"tokens":[…],"match":7},
         "pool":{"tokens":[…],"match":12,"origin_req":"…"},
         "chain":{"after_mtp":[…],"match":5}},                 // [+] facoltativo, vedi D6
 "accepted":2,"committed":3,
 "ms_measured":null,
 "cost_est":{"profile":"P2","c_verify":1.99,"c_mtp":0.177,"c_lookup":0.0,"total":2.167},
 "policy":"draft_policy@7dd5cf18|arbiter_v2@…","policy_note":"probe|stale|margin",
 "acc":{"mtp":2,"lookup":5,"pool":5},                          // [+] facoltativo/derivabile, vedi D2
 "censored":{"mtp":false,"lookup":true},                       // [+] solo live senza ref_tokens
 "policy_dbg":{"t_mtp":4,"q":0.91,"base":0.051,"best":0.064},  // [+] facoltativo, vedi D5
 "ms_split":{"verify":0,"mtp":0,"lookup":0,"commit":0},        // [+] facoltativo
 "moe":{"experts_routed":0,"experts_cpu":0,"cpu_entries":0}    // [+] facoltativo, per H5, vedi D7
}
```

| Campo | Tipo | Obbl. | Significato / regola |
|---|---|---|---|
| `r` | int | sì | indice del round nella richiesta (0-based) |
| `pos` | int | sì | numero di token di output già committati prima del round (0-based) = indice in y del primo token che il round produce. I draft si confrontano con `y[pos], y[pos+1], …`; il round committa `y[pos … pos+accepted]` — vedi D4 |
| `ctx_len` | int | sì | prompt + output committati prima del round |
| `ctx_bucket` | int | sì | come `DraftPolicy::set_context`: 0 se `ctx_len`<6000, 1 se <24000, 2 altrimenti (`draft_policy.cpp:76-96`) |
| `source` | enum | sì | fonte verificata. `none` = T=1 (anche le righe teacher-forced) |
| `k_proposed` | int | sì | draft nella finestra = T−1 |
| `T` | int | sì | righe della finestra |
| `proposal` | int[] | sì | i `k_proposed` token verificati |
| `cand.mtp.tokens/probs` | int[]/float[] | sì se MTP attivo | **sempre a profondità piena Dmax**, anche se T è più piccolo e anche se la fonte scelta è un'altra (regola 1) |
| `cand.mtp.ent` | float[] | facoltativo [+] (D11) | entropia (nat) della distribuzione del drafter MTP a ogni posizione 1..Dmax; serve allo stop per entropia/confidenza (AdaEDL `1−√(γH)`, SVIP `√H`). `probs[j]` resta la probabilità top-1 (= probabilità del token proposto, greedy) |
| `cand.lookup` | obj/null | sì se lookup attivo | `tokens` = `SuffixDrafter::propose(max_k)`, `match` = `last_match()`; `null` se nessun match ≥ min_match |
| `cand.pool` | obj/null | facoltativo (H2) | stesso significato per il pool persistente |
| `accepted` | int | sì | prefisso comune tra `proposal` e i token committati (regola 2) |
| `committed` | int | sì | = `accepted` + 1 |
| `ms_measured` | float/null | facoltativo | tempo di round (round0 → observe) |
| `cost_est` | obj | sì | ricalcolabile dal simulatore per qualunque profilo; `total` = c_verify(T)+c_mtp·d_mtp+c_lookup |
| `policy`, `policy_note` | string | sì | nome@rev della policy; motivo della scelta |

Regole (identiche al piano §6): 1) tutte le candidate ogni round, MTP a Dmax; 2) `accepted` rispetto ai token
committati; 3) `ms_measured` facoltativo, `cost_est` obbligatorio; 4) tracce teacher-forced: una riga `round` per
**ogni** posizione `pos` di y, `source:"none"`, `T:1`, `cand` pieno; 5) mappatura da `STRATA_SPEC_TRACE`
(`generate.cpp:16398-16405`, `16704-16707`): T→`T`, a→`accepted`, sfx→`source`, p*→`cand.mtp.probs`.

## 2. Accettazione controfattuale (come il replay la calcola)

Verifica greedy = match di prefisso (`generate.cpp:16643-16644`, serve `15108-15109`). Per una candidata d al round
in `pos`: `a(d) = LCP(d, y[pos : pos+len(d)])` (equivale a `a(d,i)=LCP(d, y[i+1:])` del piano §5 con `i = pos−1`, l'ultimo token committato), poi `min(a(d), T−1)` per una finestra di T righe.
- Con `ref_tokens`: esatta per qualunque candidata (anche non scelta) — **path-independence** dell'MTP assunta
  (piano Q2, gate V1). Il lookup è deterministico dato lo storico, quindi esatto senza ipotesi.
- Senza `ref_tokens` (live puro): si conoscono solo i `committed` token del round, quindi per la candidata non scelta
  `a(d)` è **censurata** a `committed` (se coincide con tutti, si sa solo `a ≥ committed`). Il campo `censored`
  lo segnala; il post-processore `replay/postprocess.py` toglie la censura quando `ref_tokens` è disponibile.
- Sotto `STRATA_SPEC_PROB` (rejection sampling) l'accettazione controfattuale non è definita: righe da escludere.

## 3. Formato interno del replay (derivato, non da produrre)

Il simulatore (`/workspace/strata-policy/replay/`) converte i file `strataplus.v1` in array per posizione:
`acc_mtp[pos]` (≤ Dmax), `p_mtp[pos][Dmax]`, `lk_k[pos]`, `lk_match[pos]`, `acc_lk[pos]`, `agree[pos]` (prefisso
comune tra `cand.mtp.tokens` e `cand.lookup.tokens`), idem per `pool`. È un dettaglio di implementazione,
descritto in `/workspace/strata-policy/replay/SCHEMA.md`.

## 4. Divergenze da piano §6 (per Strata Lead)

Nessun campo del §6 è stato rimosso o rinominato. Aggiunte e chiarimenti necessari al replay:

- **D1 — manca il flag «sintetico».** Il §6 non distingue dati misurati, teacher-forced e sintetici. Propongo
  `request.data_kind ∈ {live, teacher_forced, synthetic}` obbligatorio; il simulatore rifiuta di stampare numeri
  senza etichetta `SYNTHETIC` quando `data_kind="synthetic"`.
- **D2 — manca y in forma di token.** Il §6 ha solo `ref_output_sha256`. Per calcolare l'accettazione delle candidate
  non scelte (e O_DP, che visita posizioni non visitate dalla policy) servono gli id di y. Propongo
  `request.ref_tokens` (oppure un file accanto `<run_id>.ref.jsonl`). In alternativa minima: `round.acc.{mtp,lookup,pool}`
  calcolati dal motore, che però nel live sono censurati (vedi §2).
- **D3 — Dmax non dichiarato.** Propongo `request.dmax`; `len(cand.mtp.tokens)` deve valere `dmax` in ogni round.
- **D4 — semantica di `pos` non definita.** Fisso: `pos` = token di output già committati prima del round. In Strata
  la riga 0 della finestra è l'ultimo token committato, `outv[i]` è il token del target dopo la riga i, e il draft i+1
  è accettato se `window[i+1]==outv[i]` (`generate.cpp:15108-15109`): quindi i draft si confrontano con `y[pos…]`,
  il round committa `y[pos…pos+a]` e `pos` avanza di `a+1`. Il piano §5 indicizza con i = ultimo token committato
  (`y[i+1:]`): stessa cosa con `i = pos−1`.
- **D5 — stato interno della policy facoltativo** (`policy_dbg`): `t_mtp`, `q = lookup_rate(match)`, `base`, `best`,
  per verificare che il simulatore (che linka `strata_spec`) riproduca le scelte del motore round per round.
- **D6 — `chain` senza candidata.** Il §6 ammette `source:"chain"` ma `cand` non ha la continuazione di
  `SuffixDrafter::propose_after(drafts)` (usata da `--lookup-chain`, `generate.cpp:14906-14917`). Propongo
  `cand.chain = {after_mtp:[…], match}` facoltativo; senza, l'oracolo esclude `chain` da Ω.
- **D7 — niente campi MoE.** Per H5 (costo degli expert mancati) propongo `round.moe` facoltativo con i delta per
  round di `d.multi_misses` / `d.multi_entries` (`include/strata/core/expert_source.hpp:643-644`) e il numero di
  expert distinti instradati (come `STRATA_ROUTE_STATS`, `verify.hpp:368`). Solo motore Strata; `null` altrove.
- **D8 — `ms_split` facoltativo**: verify / mtp / lookup / commit, per stimare ρ_mtp e ρ_lu da run live invece di
  assumerli (oggi sono simbolici, piano §4).
- **D9 — campionamento.** Aggiungere a `flags` (o un campo `sampling`) se il run è greedy o `STRATA_SPEC_PROB`: con il
  secondo l'accettazione controfattuale non è definita (§2).
- **D10 — pool: chi lo ha alimentato.** `cand.pool.origin_req` c'è; serve anche, nella riga `request`, l'ordine
  di alimentazione del pool (implicito nell'ordine delle righe: lo rendo esplicito come regola in §1).

- **D11 — confidenza per posizione del drafter MTP (richiesta Strata Scout / Lead, variante H4).** `cand.mtp.probs[j]` è
  fissato come **probabilità top-1** del drafter alla posizione j (il token proposto, greedy; è ciò che riceve
  `DraftPolicy::observe_probs` / `keep_draft`). Aggiungo `cand.mtp.ent[j]` facoltativo = entropia (nat) della
  distribuzione completa del drafter alla posizione j, per valutare uno stop AdaEDL-like (stop se `1−√(γ·H_j) < λ`)
  o SVIP-like (`√H_j > h`). Costo: un softmax completo per draft, già calcolato quando c'è `--spec-min-p`; nel proxy
  llama.cpp è disponibile dai logits del drafter. Se manca, il replay usa solo `probs` (stop su confidenza top-1).
- **D12 — profilo di costo misurato P4.** Il simulatore carica `/workspace/strata-plus/traces/cost_p4_cpu.json`
  (Strata Bench, modello denso su CPU) quando esiste. Formato atteso (proposta): `{"profile":"P4","model":"…",
  "hardware":"…","s":[s(1)=1,…,s(Dmax+1)],"rho_mtp":…,"rho_lu":…,"step_ms":…,"n_samples":…,"source":"llama-bench …"}`,
  con `s` normalizzato a `s(1)=1`, `rho_*` in unità di `step_ms` per token di draft. Campi mancanti → il simulatore li
  dichiara e usa la griglia di sensibilità. Il costo degli expert mancati (H5) **non** è riproducibile su proxy densi:
  P4 vale solo per la parte densa del costo.
- **D13 — riga `request_end` (solo tracce live del motore Strata, patch P1).** Nel serve loop gli id di output sono
  noti solo a fine richiesta: P1 scrive `{"type":"request_end","schema":"strataplus.v1.1","run_id","req_id",
  "output_tokens","output_ids":[…]}` dopo l'ultima riga `round`. Il replay la usa come y (D2) per le tracce live;
  `request.ref_tokens` resta preferito quando c'è un riferimento greedy indipendente (spec off).
- **D14 — note sulle tracce proxy di Strata Bench** (`traces/LOG_SCHEMA.md` G1–G7), recepite dal replay:
  G2 `cand.mtp.probs` viene dal sampler MTP di llama.cpp (top_k=10 + temperatura), non è la top‑1 greedy di D11:
  per i gate su confidenza vale come segnale ordinale, non come probabilità calibrata; G3 il lookup del proxy è
  `SuffixDrafter` con `max_match=32` (costruttore di default) mentre `strata generate` usa 64 (`generate.cpp:16428`):
  il replay ricalcola lookup/pool dai token con la configurazione del motore (64) e lo dichiara; G7 i `ms_measured`
  del proxy (`draft`/`lookup`/`verify`) sono la base naturale per P4 (D12) ma restano tempi CPU di un modello denso.

Compatibilità (v1.1): D1–D14 approvate da Strata Lead. **Obbligatori: D1, D2 oppure D13, D3, D4**; gli altri `[+]` facoltativi.
Un lettore che ignora i campi facoltativi resta valido; i file `strataplus.v1` con i campi obbligatori sono accettati.
