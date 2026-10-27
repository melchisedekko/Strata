# ERRATA — `mtp_process_ms` in agent_v12 (tracer v12) ed E4 v14 (tracer v14) — 27/10/2026 13:25 CET
**Proxy CPU, non AMD, llama.cpp non Strata.** Questa errata non modifica nessun file: tutti i file citati restano come sono (hashati).
Nessuna misura nuova: ogni numero viene da una lettura dei file elencati, fatta il 27/10/2026 ~13:20 CET.

## Perché un file nuovo e perché questo nome
- `holdout_lookup_v12_ERRATA_2.md` (sha256 9ea774ba…) documenta l'artefatto solo per **holdout_lookup_v12** (bracci n7/n12/n16).
  Sulle altre serie dice solo che il difetto è "latente in ogni braccio lookup-only/ydiag/base dei tracer v11-v13", senza dati.
- Non copre: (a) i numeri della serie **agent_v12** (tracer v12, scritta dopo l'ERRATA_2); (b) il fatto che il flag dei tempi di agent_v12
  non è arrivato alle righe request; (c) la verifica che la correzione v14 funziona in E4; (d) i valori `-nan` nelle tracce E4 dvocab.
- Il nome `ERRATA_mtp_process_ms_agent_v12_e4v14.md` dice il campo e le due serie. Non è "ERRATA_3" di holdout_lookup_v12 perché non
  riguarda quella serie.

## (a) agent_v12: il braccio lookup-only ha lo stesso artefatto
Tracer: `llama_spec_trace.v12.nollamafile` (sha256 6c31c21e…, da AGENT_V12_READY). Il braccio `agent_v12_live_lookup` gira con
`--mode live --live-src lookup` (agent_v12/cmds.txt), quindi `spec = nullptr`: è la stessa causa descritta nell'ERRATA_2 (sez. "Causa").
I tempi sono annidati: `stats.mtp_process_ms` (riga request) e `ms_split.mtp_process` (riga round).

| braccio | richieste con stats.mtp_process_ms > 0 | min / max per richiesta (ms) | round con ms_split.mtp_process > 0 | somma mtp_process / somma verify_ms |
|---|---|---|---|---|
| live_lookup (nessun contesto MTP) | 23/23 | 0.004 / 0.015 | 7 / 978 | 1.47e-6 |
| tf_d7 (contesto MTP vero) | 23/23 | 73.484 / 613.783 | 1470 / 1470 | 0.0718 |
| live_mtp_k3 (contesto MTP vero) | 23/23 | 68.839 / 1111.154 | 565 / 565 | 0.0951 |
| live_combo (contesto MTP vero) | 23/23 | 77.483 / 1054.607 | 507 / 507 | 0.0773 |

- Nel braccio live_lookup `mtp_process_ms` è il costo del cronometro, non lavoro MTP: **non valido**, da leggere come "nessun contesto MTP".
- Negli altri tre bracci il valore è lavoro MTP reale, ma **tutti i tempi di agent_v12 sono comunque "non usabili come misura"**
  (decisione del Lead 25/10 08:24, carico CPU estraneo; testo nell'header di ogni file e in AGENT_V12_READY).
- AL, greedy_equal_ref e first_divergence_pos non dipendono da questo campo e restano validi.

## (b) agent_v12: il flag "non usabili" sta solo nell'header
- `agent_v12/agent_v12_timing_flag.py` (nel MANIFEST di agent_v12) cerca i campi di tempo al **primo livello** delle righe request e
  request_end (`k in TK or k.endswith('_ms')`). In agent_v12 i tempi sono annidati in `stats` / `ms_split`, quindi la ricerca non trova nulla.
- Conteggio letto dai file: righe request/request_end con `timing_validity` = **0** in tutti e 4 i file; header con `timing_validity` = **1**
  per file.
- Effetto: **nessuno sulla validità**. La regola resta quella dell'header e di AGENT_V12_READY (`timing_validity`: tempi non usabili
  come misura, intera serie). Chi legge una riga request deve applicare il flag dell'header. I file non si riscrivono (sono nel MANIFEST).

## (c) E4 v14: la correzione funziona; tutti i bracci E4 hanno contesto MTP
Tracer v14 (`proxy/llama_spec_trace_v14.cpp`, sha256 ddea7320…): `proc_ms = spec ? ms_since(tp) : -1.0` (L403), `null` per round
(L451), somma solo con `spec` (L454), `mtp_process_ms`/`mtp_ctx` per richiesta (L500-501).
- I 6 file E4 (`e4v14_tf_d7_p30_{full,dvocab,dvocab_en}` × {code+chat, edit_np}) sono tutti in modalità TF con contesto MTP:
  `mtp_ctx = true` in tutte le richieste (20 + 10 per braccio), `mtp_process_ms > 0` in tutte, `ms_measured.mtp_process > 0`
  in 2459/2479 righe round (code+chat) e 1280/1290 (edit_np) per braccio. Nessun `null`: in E4 non c'è un braccio senza contesto MTP,
  quindi il ramo `null` di v14 qui **non è esercitato** (sarà esercitato solo dai bracci senza MTP, se ce ne saranno).
- Manifest nuovo delle uscite E4 (E4 per design non ne scriveva uno): `traces/raw/v11/e4v14_MANIFEST.sha256` (29 file,
  sha256 101be0576218708ca5aa1296997e3c9be1f4d568828fcc607c82ef01846f12a1), solo hash dei file esistenti, nessun file modificato.

## (d) E4 v14: `-nan` nel campo `cand.mtp.ent` dei bracci dvocab / dvocab_en
- Nei 4 file dvocab e dvocab_en (code+chat ed edit_np) **ogni** riga round ha `"ent":[-nan,…]`: 17213/17213 valori (code+chat) e
  8960/8960 (edit_np) per braccio. Nel braccio full: 0 nan su 17213 (code+chat).
- Le righe con `-nan` (2459 e 1280 per file) **non sono JSON valido in senso stretto**: `json.loads` di Python le rifiuta. Per leggerle si
  sostituisce `-nan` con `NaN` prima del parsing; nessun altro campo cambia.
- Origine: il tracer stampa `ent` con `%.4f` (v14 L435). Il valore nan arriva dal calcolo dell'entropia sul vocabolario ristretto del draft;
  il punto esatto del codice **non è verificato** (ipotesi: termini p·log p con p = 0 fuori dal vocabolario ridotto).
- Validità: `cand.mtp.ent` dei bracci dvocab/dvocab_en **non è usabile**. tokens, probs, accettazioni e AL non dipendono da `ent`.
  I file non si riscrivono.

## File letti (nessuno modificato)
- traces/agent_v12/: MANIFEST.sha256 (sha256 f876985fda9575525bd70896c1f9155da283c3cf87444863ce1d8574c8271e0a, 21 file, sha256sum -c OK
  il 27/10 13:1x CET), AGENT_V12_READY (3727d47b…), agent_v12_{tf_d7,live_mtp_k3,live_lookup,live_combo}.jsonl, cmds.txt,
  agent_v12_timing_flag.py.
- traces/raw/v11/: e4v14_* (vedi e4v14_MANIFEST.sha256), campaign.log (exit 0 per i 6 bracci, "run_e4_v14.sh exit 0" 27/10 11:57:13 CET).
- traces/holdout_lookup_v12_ERRATA_2.md (9ea774ba…), proxy/llama_spec_trace_v14.cpp (ddea7320…).
