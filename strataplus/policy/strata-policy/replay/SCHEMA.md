# Formato interno del replay (derivato)

Il formato da produrre è **`/workspace/strata-plus/log_format.md`** (`strataplus.v1`, piano §6 + divergenze D1–D14).
Questo file descrive solo gli array che `strata_sim/postprocess.py::load_tf` (tracce teacher-forced o live con
`request_end`, D13) e `strata_sim/synth2.py` (dati SINTETICI) costruiscono per ogni richiesta, consumati da
`strata_sim/sim2.py`:

| chiave | forma | significato |
|---|---|---|
| `n` | int | token di output (len y) |
| `y` | int32[n] | output di riferimento (`request.output_ids` / `ref_tokens` / `request_end.output_ids`) |
| `mtp_tok`, `mtp_p`, `mtp_ent` | [n, Dmax] | candidate MTP a profondità piena alla posizione `pos` (D3, D4, D11; ent = NaN se assente) |
| `mtp_acc` | int[n] | LCP(mtp_tok[pos], y[pos:]) ≤ Dmax |
| `lk_k`, `lk_m`, `lk_acc`, `lk_tok`, `agree` | int[n] (+tok [n,Dmax]) | lookup per richiesta (SuffixDrafter di produzione, `max_match=64`, ricalcolato), accettazione, accordo del primo token con MTP |
| `pl_*`, `agree_pl` | int[n] | idem per il pool persistente (scope dominio o sessione, alimentato in ordine di richiesta, D10) |
| `session`, `domain`, `label`, `data_kind`, `target_mismatch` | | cluster del bootstrap, dominio, etichetta dei dati (SYNTHETIC / proxy CPU / live), righe in cui `target_tokens[0]≠y` (controllo di coerenza) |

Accettazione controfattuale: §2 di log_format.md (censura a a+1 nelle tracce live).
