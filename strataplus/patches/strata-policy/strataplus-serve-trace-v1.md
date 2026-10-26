# strataplus-serve-trace-v1 — trace per-round di `strata serve` (patch di misura, OFF di default)

Patch di sola misura, comune a P-H1, P-LANG e P-HFC. Si attiva con `STRATA_SERVE_TRACE=<file>`; senza questa variabile non cambia nulla.

## Varianti (stesso codice, cambiano solo le righe di contesto)
| file | base dichiarata | `git apply --check` OK su |
|---|---|---|
| strataplus-serve-trace-v1.patch | b24c6a1d (controllo) | b24c6a1d, 7dd5cf1 |
| strataplus-serve-trace-v1-on-H1v2.patch | b24c6a1d + H1-arbiter-v2 | solo questa |
| strataplus-serve-trace-v1-on-H1v2-LANGv2.patch | b24c6a1d + H1-arbiter-v2 + LANG-knob-v2 | solo questa |
| strataplus-serve-trace-v1-on-HFCv2.patch | 7dd5cf1 + strataplus-HFC-frozen-v2 (Scout) | 7dd5cf1+HFCv2, b24c6a1d+HFCv2 |

Ogni variante ha il suo file `.sha256`. Ogni variante dà `--check` negativo su tutte le basi tranne la propria. HFC-v2 non si applica sopra H1v2+LANGv2: quella combinazione non esiste, e la limitazione viene da HFC-v2, non da questa patch.
Le varianti sono state generate con `/workspace/policy-local/serve_trace/apply_serve_trace.py <tree>`, che inserisce le modifiche cercando delle stringhe di ancoraggio.

## Contenuto
- Nuovi file: `include/strata/spec/serve_trace.hpp`, `src/spec/serve_trace.cpp` (con SHA-256 proprio) e `src/spec/serve_trace_test.cpp`.
- CMake: `target_sources(strata_spec PRIVATE src/spec/serve_trace.cpp)` e un target/test `serve_trace_test` dentro `STRATA_BUILD_TESTS`.
- `src/program/generate.cpp`, 6 punti di aggancio (righe dopo la patch; ogni riga porta il commento `// Strata+ serve-trace v1`):

| aggancio | b24c6a1d | 7dd5cf1 | H1v2 | H1v2+LANGv2 | HFCv2 (7dd) |
|---|---|---|---|---|---|
| include | 90 | 89 | 90 | 90 | 89 |
| init: dopo il parsing degli argomenti, prima del caricamento del modello | 2802 | 2797 | 2955 | 2967 | 2831 |
| begin richiesta (dopo `const char* finish = "length";`) | 14245 | 14209 | 14420 | 14461 | 14251 |
| pipeline_t (dopo `tre("V", A.seq, a, …)`) | 14803 | 14767 | 14978 | 15023 | 14809 |
| serial (prima di `policy.observe_probs(dwin_s…)`, solo `timed_round`) | 15268 | 15205 | 15478 | 15525 | 15247 |
| end + flush (prima della riga `YIELDED`/`DONE`) | 15461 | 15398 | 15719 | 15766 | 15440 |

  I punti indicati dal Lead (L15146/L15176 serial, L14616/L14729 pipeline) sono stati verificati e agganciati per ancora (verdetto `V` e `observe_probs`), non per numero di riga.
- `sycl/src/program/generate.cpp` L1735: se la variabile è impostata, stampa su stderr `warning: STRATA_SERVE_TRACE ignorata su SYCL`.

## Schema (append; una riga per round verificato)
```
# strata serve trace v1 fields: T a sfx ms p1..p{S-1} path= req= lang= src= arb= frozen= | joint=0|1 det=0|1 frozen=0|1 frozen_value=<env> frozen_sha256=<hex|->
# req=<n> begin lang=<strata_lang|->
<T> <a> <sfx> <ms %.3f> <p1 %.4f> ... <p{S-1}>  path=serial|pipeline_t req=<n> lang=<..|-> src=mtp|lookup arb=off|joint|det frozen=0|1
# req=<n> end finish=<stop|length|…> produced=<token> rounds=<n>
```
- **Campi CLI.** Hanno lo stesso ordine e formato di `STRATA_SPEC_TRACE` (`"%d %d %d %.3f"` + `" %.4f"`×(S-1), con S ≤ 9):
  - T = righe della finestra;
  - a = draft accettati nella verifica;
  - sfx = 1 se la finestra viene dal lookup/suffix;
  - p = probabilità MTP della finestra.
- **ms.** Il significato dipende dal percorso:
  - `serial`: `Clock::now() - round0`, come nella CLI e in `policy.observe`;
  - `pipeline_t`: `ms_now() - last_verdict`, la stessa quantità che `policy.observe` riceve nella pipeline.
- **src.** `mtp` oppure `lookup`, cioè la sorgente scelta (`sfx`).
- **arb.** Modo dell'arbitro letto dall'env (`STRATA_SPEC_JOINT_DET` → det, `STRATA_SPEC_JOINT` → joint, altrimenti off). La decisione dell'arbitro si vede nel T e nel src del round.
- **frozen.** Vale 1 quando `STRATA_SPEC_COST_FROZEN` è impostato, sia il flag `1` di H1 sia un `<path>` di HFC. Se il valore è un file leggibile, l'header riporta il suo sha256, altrimenti `-`. I valori vengono solo dall'env, quindi nessuna dipendenza dal codice H1/HFC.
- **lang.** Il token `strata_lang=` della riga GEN, con valori validi `[A-Za-z0-9_+#.-]{1,32}`, altrimenti `-`.
- **req.** Contatore progressivo per processo.

## Garanzie
- **Flag off.** Unset o vuoto: nessun file creato (test), nessuna scrittura, solo un `bool` controllato per round. stdout non viene toccato in nessun caso: la patch non aggiunge `printf` su stdout in generate.cpp (controllo statico sul diff), quindi le righe GEN/serve, `DONE` e `YIELDED` restano identiche. `server.py` non è toccato.
- **Path non scrivibile.** `strata serve: STRATA_SERVE_TRACE: cannot open <path> for writing` e rc=1, prima di caricare il modello. Fuori da `serve` (CLI) la variabile viene ignorata con un warning su stderr.
- **Scrittura fuori dal percorso critico.** Durante la richiesta i round vanno in un buffer in memoria; a fine richiesta c'è un solo `fwrite` + `fflush`. **Overhead NON misurato.**

## Test (CET, 26/10/2026; nessun modello lanciato; nice 19)
- **22:39** — `g++` standalone del modulo + `serve_trace_test`: rc=0, 22/22 ok. Il test copre:
  - vettori SHA-256;
  - `lang_of`;
  - off ⇒ nessun file;
  - path non scrivibile ⇒ errore;
  - buffering fino a end;
  - formato esatto delle righe serial e pipeline;
  - header con joint/det/frozen e sha;
  - append.
- **22:40–22:42** — syntax-check HIP di generate.cpp su b24+trace, H1v2+LANGv2+trace, 7dd5cf1+trace, 7dd5cf1+HFCv2+trace, H1v2+trace e b24+HFCv2+trace: rc=0 per tutti, 131 warning, lo stesso numero del controllo.
- **22:41** — build host CMake (strata_spec + test) su b24+trace e H1v2+LANGv2+trace: rc=0; ctest 4/4 (serve_trace, suffix_drafter, controller, draft_policy).
- **22:42** — matrice `git apply --check`: vedi la tabella delle varianti.
- **Non eseguiti:** build HIP completa (pronta in `/workspace/policy-local/hip_build_full_rocm644_v2.sh`, build (4) e (5)), compilazione SYCL e CUDA, host build delle varianti H1v2/HFC (pronta in `/workspace/policy-local/host_build_serve_trace.sh`).

## Limiti
- I campi interni dell'arbitro H1 (T proposto prima dell'arbitro, punteggi) non sono nella patch comune, che vede solo l'env, il T finale e src.
- Le richieste BGEN/batched non hanno un'etichetta propria. Il percorso Qwen3.5/qwen35 e la CLI non sono tracciati.
- SYCL: solo il warning.
- `pipeline_t` traccia ogni verdetto; `serial` traccia solo i round `timed_round`, come la CLI, quindi senza la prima finestra.
- L'overhead non è misurato.
