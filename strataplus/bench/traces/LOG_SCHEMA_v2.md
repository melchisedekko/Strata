# LOG_SCHEMA v2 — campi del tracer v14 (schema "strataplus.v1.1", proxy CPU, non AMD)
La v1 (traces/LOG_SCHEMA.md, sha256 239bb437bf2bce6c7ea7b0a48a4d813f0e22dffbaf6841cbe028c56a69580997) resta valida.
Qui ci sono solo le aggiunte e i cambi di proxy/llama_spec_trace_v14.cpp (sha256 ddea7320…). Lo schema resta "strataplus.v1.1".
La stringa `tracer` della riga request inizia con "llama_spec_trace_v14 (".

## Round
| campo | significato |
|---|---|
| `committed` | token davvero aggiunti all'output: si ferma al primo EOG del round, EOG incluso (da v13). |
| `committed_raw` | `ids.size()`, cioè il valore che v11/v12 scrivevano come committed. |
| `eos_clamped` | true se committed < committed_raw. |
| `accepted` | min(accepted_raw, committed). |
| `ms_measured.mtp_process` | ms di `common_speculative_process`; **null** se non c'è contesto MTP (bracci lookup-only o base). Prima era un residuo del cronometro: ERRATA 2. |
| `cand.mtp` | tokens (cap = --spec-draft-n-max), probs (top-1 softmax full-vocab a temp 1), ent, probs_sampler (vecchio campo: p del sampler, softmax rinormalizzata su top_k=10). |
| `cand.lookup` | tokens (SuffixDrafter(3,64).propose(dmax), non troncato) e match. |
| `arbiter` | **solo con --live-src aprime\|default_a.** Contiene impl ("strata_arbiter_v1"), arm, S, S_mtp, spec_min_p, first_window, k_full, k_used = min(k_full, S-1), match, t_mtp (T dopo min_p), gate, choose_called, lookup, T_pre_room, room (= 1 + n_draft_max), T, q (lookup_rate(match) prima della scelta), mtp_tokens_tmtp, rounds_before, observed. |

## Request
| campo | significato |
|---|---|
| `mtp_process_ms` | somma dei valori di round; **null** senza contesto MTP. |
| `mtp_ctx` | true/false: indica se esiste un contesto MTP. |

## Nuovi flag CLI del tracer v14
- `--live-src aprime`: S=8, S_mtp=4, min_p 0.
- `--live-src default_a`: S=6, S_mtp=4, min_p 0.5.
- Entrambi richiedono `--dmax 7 --spec-draft-n-max 3` e rifiutano ckpt_tgt e i bracci senza MTP.
- `--arb-s s1,..,s8`: s(T) fisso alternativo. Default kShape.
- Lo stato dell'arbitro si resetta a ogni prompt.
