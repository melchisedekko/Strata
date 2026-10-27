# Esattezza del rollback dello stato ricorrente: verifica v1 (PREREG v2, Parte B), edit_np, solo aggregati
Proxy CPU, non AMD. Stessa build, stesso modello, stessi comandi e stessi limiti di rollback_exactness_v1.md (incluse la sovrapposizione con la run aprime_tm0 di Bench, PID 780678, e il fatto che nessun tempo di questa finestra va usato).
I dati per prompt restano locali (/workspace/policy-local/arbiter_diag/). 7 prompt divergenti, bracci A1 e B1.

## Verdetto (PREREG v2 sha256 72cac436…63a3, addenda 1-3): **ESATTO**
- 113/113 round validi: vmargin del round r+1 riprodotti, ogni seq_rm=true.
- N1=0, N2=0, E1/E2/E3 soddisfatti.
- F_log = F_state = 0: (a)-(a') e (c)-(c') sono bit-identici in 113/113 round.
- Il controllo GGML_CPU_TILED_MM=0 non è stato eseguito (rinviato); il verdetto non ne dipende.

| confronto | round | stato bit-identico | logit (tutte le righe Q) bit-identici | max\|Δ\| riga0 max / p99 / mediana | max\|Δl1\| riga0 | flip top-1 (margine rif.) | flip con margine > τ |
|---|---|---|---|---|---|---|---|
| (a)-(a') | 113 | 113 | 113 | 0 / 0 / 0 | 0 | 0 | 0 |
| (c)-(c') | 113 | 113 | 113 | 0 / 0 / 0 | 0 | 0 | 0 |
| (a)-(d) | 113 | 113 | 113 | 0 / 0 / 0 | 0 | 0 | 0 |
| (a)-(b) | 113 | 70 | 70 | 0.794646 / 0.756695 / 0 | 0.375723 | 1 (0.026896) | 0 |
| (a)-(c) | 113 | 0 | 0 | 1.227577 / 1.067740 / 0.677885 | 0.459482 | 0 | 0 |

Max|Δ| delle sezioni di stato:
- (a)-(b), 43 round diversi: kv_k 0.443, kv_v 0.398, conv 0.767, rec 0.0680.
- (a)-(c): kv_k 1.161, kv_v 0.766, conv 0.950, rec 0.137.

Per braccio:
- A1: 71 round.
  - (a)-(d): 71/71 bit.
  - (a)-(b): 43/71 stato bit, max|Δ| 0.794646, 1 flip.
  - (a)-(c): max|Δ| 1.227577, 0 flip.
- B1: 42 round.
  - (a)-(d): 42/42 bit.
  - (a)-(b): 27/42 stato bit, max|Δ| 0.756695.
  - (a)-(c): max|Δ| 0.997446, 0 flip.

Strati:

| strato | round | (a)-(d) bit | (a)-(b) stato bit | (a)-(b) max\|Δ\| riga0 | (a)-(c) max\|Δ\| riga0 |
|---|---|---|---|---|---|
| T_r < 8 | 107 | 107 | 70 | 0.794646 | 1.067740 |
| T_r ≥ 8 | 6 | 6 | 0 | 0.726940 | 1.227577 |
| T_q = 1 | 3 | 3 | 3 | 0 | 0.793428 |
| T_q ≥ 2 | 110 | 110 | 67 | 0.794646 | 1.227577 |

Le attribuzioni (tiled per T_r ≥ 8, FA per T=1) restano ipotesi non verificate: il controllo è rinviato. Nulla è attribuito al GDN (Addendum 3).
