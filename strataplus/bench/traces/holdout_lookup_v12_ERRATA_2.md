# ERRATA 2 holdout_lookup_v12 (proxy CPU, non AMD) — 26/10/2026 19:37 CET
I file di traces/holdout_lookup_v12/ (MANIFEST.sha256 30ebe146…, READY 22234b4d…) e l'ERRATA 1 (holdout_lookup_v12_ERRATA.md, sha256 59f9de02…)
**non sono modificati**. Questa errata documenta una seconda anomalia, segnalata da Policy: `mtp_process_ms > 0` in tutte le 90 richieste
di ciascun braccio, anche se i bracci lookup-only non hanno contesto MTP.

## Dati (letti dai trace, nessuna misura nuova)
| braccio | richieste con mtp_process_ms > 0 | min / max per richiesta (ms) | round con ms_measured.mtp_process > 0 | somma mtp_process / somma verify |
|---|---|---|---|---|
| n7  | 90/90 | 0.002 / 0.025 | 3 / 5227 | 2.29e-6 |
| n12 | 90/90 | 0.002 / 0.018 | 3 / 4909 | 2.29e-6 |
| n16 | 90/90 | 0.001 / 0.011 | 2 / 4802 | 1.25e-6 |

## Causa (sorgente del tracer)
Binario dei tre bracci: proxy/llama_spec_trace.v11.bin (sha256 f3f3ef188648ca9e…, cmds.txt in holdout_lookup_v12/). Il sorgente esatto di quel
binario non è conservato byte per byte: il binario (mtime 25/10 02:42:31 ora del box) non contiene la stringa `--p4-tlist` presente in
proxy/llama_spec_trace.cpp (mtime 02:08:12), quindi viene da una revisione intermedia non conservata;
le stringhe di formato del binario (`strings`) coincidono con quelle del sorgente, e il codice coinvolto è identico in tutte le versioni
v11 → v13. Righe in proxy/llama_spec_trace.cpp (sha256 62f1ffb7…) [e in llama_spec_trace_v12.cpp, sha256 911d6a29…]:
1. `--live-src lookup` ⇒ `lookup_only = true` (L98) ⇒ `base = mode == "base" || lookup_only` (L110 [L116]): nessun contesto MTP
   (`if (!base)` salta `common_speculative_init_from_params`, L125 [L131]) e `spec = nullptr` per ogni prompt (L171 [L179]).
2. Nel ciclo di round: `const auto tp = Clock::now();` (L353 [L361]), poi `if (spec && !common_speculative_process(spec, batch_tgt))`
   (L354 [L362]) che con `spec == nullptr` non esegue nulla, poi `const double proc_ms = ms_since(tp);` (L355 [L363]).
   Il cronometro misura quindi solo due chiamate a `steady_clock::now()` e un confronto (decine di ns).
3. `proc_ms_tot += proc_ms` (L401 [L409]) somma questo residuo su ~55 round per richiesta in double; la riga request lo stampa con %.3f
   (`"mtp_process_ms":%.3f`, L445-447 [L453-455]) ⇒ 0.001–0.025 ms. Per round lo stampa con %.3f (L396-398 [L404-406]) ⇒ quasi sempre 0.000.
**Conclusione:** il tracer non esegue lavoro MTP; il valore > 0 è il costo del cronometro, non lavoro MTP. Il campo è un artefatto di misura.

## Validità
- `mtp_process_ms` (request) e `ms_measured.mtp_process` (round) di holdout_lookup_v12: **non validi** (da leggere come "nessun contesto MTP").
- Regola del Lead (26/10): se il tracer segna lavoro MTP inesistente, i tempi di quei trace si dichiarano non validi. Quindi **tutti i campi di
  tempo di holdout_lookup_v12 sono non validi come misura.** Per la decisione: il residuo è ≤ 0.025 ms per richiesta, ~2e-6 del verify_ms.
- Non toccati: AL, greedy_equal_ref, first_divergence_pos, accettazioni (conteggi deterministici; per committed oltre EOS vale l'ERRATA 1).
- Stesso difetto latente in ogni braccio lookup-only/ydiag/base dei tracer v11-v13 (stesso codice). Anche in quei bracci il campo va letto come artefatto.

## Correzione nel tracer nuovo
proxy/llama_spec_trace_v14.cpp (sorgente nuovo; v12/v13 non toccati): `proc_ms = spec ? ms_since(tp) : -1.0` (L403); somma solo con `spec`
(L454); scritto `null` per round (L451) e per richiesta, più `"mtp_ctx": false` (L500-501). Lo usano E4 (run_e4_v14.sh) e la run (a').
