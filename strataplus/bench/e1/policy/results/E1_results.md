# E1 — limite superiore model-free per H2 (pool persistente vs lookup per richiesta)

**Natura dei dati:** testi REALI di riferimento (non output greedy di un modello), tokenizzati con il tokenizer Qwen3.5-2B; accettazione = LCP(proposta, y[pos:]) con `SuffixDrafter` di PRODUZIONE (strata-src @ 7dd5cf18, via ctypes). Nessun MTP. tok/s **stimati** con i profili simbolici del piano §4 (P1/P2 = stime pubblicate nel codice, non misure; B-flat/B-lin = limiti), ρ_lu = 0.001 per token proposto o sondato (ipotesi ≈20 µs/token su ~20,5 ms di step). Walk teacher-forced *lookup-only*: si drafta min(k,K) ogni volta che il drafter propone, altrimenti step normale. IC95 = bootstrap a cluster (sessione = storia di un file per i domini session_*, richiesta altrimenti), 2000 campioni, appaiato.

## Dominio `code` — 664 richieste, 664 cluster, 39807 token di y, sorgenti: humaneval, mbpp

| sorgente | copertura (pos. con proposta) | P(a≥1 \| proposta) | acc. media \| proposta | AL K=5 | AL K=7 | righe sprecate M4 (K=7) |
|---|---|---|---|---|---|---|
| lookup | 15.1% | 54.4% | 1.49 | 1.084 | 1.087 | 83.6% |
| pool_domain | 54.6% | 44.0% | 1.11 | 1.303 | 1.312 | 89.0% |
| fallback_domain | 54.6% | 44.1% | 1.10 | 1.304 | 1.312 | 88.9% |
| best_domain | 30.9% | 78.4% | 1.99 | 1.305 | 1.313 | 76.8% |

Guadagno relativo vs lookup per richiesta (IC95), K=7: AL e speedup stimato = N·s(1)/ΣT_round

| sorgente | ΔAL | Δspeedup P1 | Δspeedup P2 | Δspeedup B-flat | Δspeedup B-lin |
|---|---|---|---|---|---|
| pool_domain | +20.7% [+19.0%, +22.4%] | -29.5% [-30.5%, -28.5%] | -30.1% [-31.0%, -29.2%] | +20.4% [+18.9%, +22.1%] | -51.6% [-52.7%, -50.4%] |
| fallback_domain | +20.7% [+19.2%, +22.4%] | -29.4% [-30.4%, -28.5%] | -30.1% [-31.0%, -29.2%] | +20.5% [+18.7%, +22.1%] | -51.6% [-52.7%, -50.4%] |
| best_domain | +20.8% [+19.2%, +22.6%] | -3.7% [-4.3%, -3.0%] | -4.1% [-4.8%, -3.5%] | +20.7% [+19.2%, +22.5%] | -21.3% [-22.4%, -20.2%] |

Walk con gate sul match (match≥6, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)

| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |
|---|---|---|---|---|---|---|
| lookup | 1.025 | 0.982 | 0.981 | — | — | — |
| pool_domain | 1.087 | 0.909 | 0.905 | -7.4% [-8.0%, -6.8%] | -7.7% [-8.3%, -7.0%] | -22.3% [-23.4%, -21.1%] |
| fallback_domain | 1.086 | 0.912 | 0.908 | -7.1% [-7.8%, -6.5%] | -7.4% [-8.1%, -6.8%] | -21.8% [-23.0%, -20.6%] |
| best_domain | 1.087 | 0.984 | 0.981 | +0.2% [-0.2%, +0.7%] | +0.1% [-0.4%, +0.6%] | -7.5% [-8.2%, -6.8%] |

Walk con gate sul match (match≥12, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)

| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |
|---|---|---|---|---|---|---|
| lookup | 1.004 | 0.989 | 0.988 | — | — | — |
| pool_domain | 1.020 | 0.994 | 0.993 | +0.6% [+0.3%, +0.9%] | +0.5% [+0.3%, +0.9%] | -1.2% [-1.5%, -0.9%] |
| fallback_domain | 1.020 | 0.994 | 0.993 | +0.5% [+0.3%, +0.9%] | +0.5% [+0.2%, +0.8%] | -1.1% [-1.4%, -0.9%] |
| best_domain | 1.020 | 0.996 | 0.995 | +0.7% [+0.4%, +1.0%] | +0.7% [+0.4%, +1.0%] | -0.8% [-1.0%, -0.6%] |

Speedup stimato assoluto (K=7) N·s(1)/ΣT_round: lookup: P1 0.907, P2 0.903, B-flat 1.086, B-lin 0.709; pool_domain: P1 0.639, P2 0.631, B-flat 1.307, B-lin 0.343

P(a≥j | T>j), lookup, j=1..7: 0.45 0.25 0.16 0.10 0.07 0.05 0.04
P(a≥j | T>j), pool_domain, j=1..7: 0.36 0.17 0.09 0.06 0.04 0.03 0.02

P(a≥1 | match bucket) [n]: lookup: m3: 0.49 [2407], m4: 0.59 [2716], m8: 0.68 [654], m16: 0.27 [241]; pool_domain: m3: 0.34 [9177], m4: 0.47 [10017], m8: 0.66 [1924], m16: 0.66 [607]

## Dominio `chat` — 399 richieste, 399 cluster, 27912 token di y, sorgenti: dolly

| sorgente | copertura (pos. con proposta) | P(a≥1 \| proposta) | acc. media \| proposta | AL K=5 | AL K=7 | righe sprecate M4 (K=7) |
|---|---|---|---|---|---|---|
| lookup | 15.1% | 70.3% | 2.93 | 1.105 | 1.110 | 73.1% |
| pool_domain | 21.6% | 52.9% | 2.10 | 1.114 | 1.119 | 86.1% |
| fallback_domain | 21.6% | 53.0% | 2.10 | 1.114 | 1.119 | 86.1% |
| best_domain | 15.9% | 71.8% | 2.85 | 1.114 | 1.119 | 74.1% |

Guadagno relativo vs lookup per richiesta (IC95), K=7: AL e speedup stimato = N·s(1)/ΣT_round

| sorgente | ΔAL | Δspeedup P1 | Δspeedup P2 | Δspeedup B-flat | Δspeedup B-lin |
|---|---|---|---|---|---|
| pool_domain | +0.8% [+0.7%, +1.0%] | -12.0% [-13.0%, -11.0%] | -12.2% [-13.2%, -11.3%] | +0.8% [+0.6%, +0.9%] | -23.6% [-25.1%, -22.1%] |
| fallback_domain | +0.8% [+0.7%, +1.0%] | -12.0% [-12.9%, -11.0%] | -12.2% [-13.3%, -11.3%] | +0.8% [+0.7%, +0.9%] | -23.6% [-25.2%, -22.0%] |
| best_domain | +0.8% [+0.7%, +1.0%] | -0.8% [-1.0%, -0.7%] | -0.9% [-1.0%, -0.7%] | +0.8% [+0.7%, +1.0%] | -2.7% [-3.2%, -2.3%] |

Walk con gate sul match (match≥6, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)

| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |
|---|---|---|---|---|---|---|
| lookup | 1.054 | 1.013 | 1.012 | — | — | — |
| pool_domain | 1.056 | 0.977 | 0.975 | -3.6% [-4.1%, -3.1%] | -3.7% [-4.2%, -3.2%] | -8.7% [-10.0%, -7.7%] |
| fallback_domain | 1.056 | 0.977 | 0.975 | -3.5% [-4.1%, -3.1%] | -3.6% [-4.2%, -3.2%] | -8.7% [-9.9%, -7.6%] |
| best_domain | 1.056 | 1.011 | 1.010 | -0.2% [-0.3%, -0.1%] | -0.2% [-0.3%, -0.2%] | -0.8% [-1.0%, -0.5%] |

Walk con gate sul match (match≥12, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)

| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |
|---|---|---|---|---|---|---|
| lookup | 1.032 | 1.016 | 1.016 | — | — | — |
| pool_domain | 1.032 | 1.016 | 1.016 | +0.0% [+0.0%, +0.0%] | +0.0% [+0.0%, +0.0%] | +0.0% [+0.0%, +0.0%] |
| fallback_domain | 1.032 | 1.016 | 1.016 | +0.0% [+0.0%, +0.0%] | +0.0% [+0.0%, +0.0%] | +0.0% [+0.0%, +0.0%] |
| best_domain | 1.032 | 1.016 | 1.016 | +0.0% [+0.0%, +0.0%] | +0.0% [+0.0%, +0.0%] | +0.0% [+0.0%, +0.0%] |

Speedup stimato assoluto (K=7) N·s(1)/ΣT_round: lookup: P1 0.963, P2 0.960, B-flat 1.108, B-lin 0.788; pool_domain: P1 0.848, P2 0.842, B-flat 1.117, B-lin 0.602

P(a≥j | T>j), lookup, j=1..7: 0.59 0.37 0.27 0.21 0.17 0.15 0.13
P(a≥j | T>j), pool_domain, j=1..7: 0.34 0.18 0.13 0.10 0.08 0.07 0.06

P(a≥1 | match bucket) [n]: lookup: m3: 0.57 [1241], m4: 0.62 [1609], m8: 0.87 [575], m16: 0.96 [802]; pool_domain: m3: 0.39 [2134], m4: 0.43 [2484], m8: 0.84 [602], m16: 0.96 [802]

## Dominio `edit` — una richiesta per cluster, 43542 token di y, sorgenti: edit_np

| sorgente | copertura (pos. con proposta) | P(a≥1 \| proposta) | acc. media \| proposta | AL K=5 | AL K=7 | righe sprecate M4 (K=7) |
|---|---|---|---|---|---|---|
| lookup | 87.1% | 90.0% | 5.60 | 3.217 | 3.650 | 28.4% |
| pool_domain | 90.2% | 88.1% | 5.39 | 3.341 | 3.809 | 35.8% |
| fallback_domain | 90.2% | 88.5% | 5.44 | 3.361 | 3.834 | 34.9% |
| best_domain | 88.6% | 90.2% | 5.54 | 3.362 | 3.834 | 29.4% |

Guadagno relativo vs lookup per richiesta (IC95), K=7: AL e speedup stimato = N·s(1)/ΣT_round

| sorgente | ΔAL | Δspeedup P1 | Δspeedup P2 | Δspeedup B-flat | Δspeedup B-lin |
|---|---|---|---|---|---|
| pool_domain | +4.4% [+3.5%, +5.4%] | -5.6% [-6.7%, -4.4%] | -5.7% [-6.8%, -4.5%] | +4.3% [+3.4%, +5.3%] | -8.7% [-10.6%, -6.9%] |
| fallback_domain | +5.0% [+4.1%, +6.1%] | -4.7% [-5.9%, -3.7%] | -4.8% [-5.9%, -3.8%] | +5.0% [+4.1%, +6.0%] | -7.8% [-9.6%, -6.1%] |
| best_domain | +5.1% [+4.1%, +6.1%] | +0.1% [-0.2%, +0.5%] | +0.1% [-0.2%, +0.4%] | +5.0% [+4.1%, +6.1%] | -1.5% [-2.0%, -1.1%] |

Walk con gate sul match (match≥6, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)

| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |
|---|---|---|---|---|---|---|
| lookup | 3.064 | 1.615 | 1.595 | — | — | — |
| pool_domain | 3.169 | 1.606 | 1.585 | -0.6% [-0.9%, -0.3%] | -0.6% [-1.0%, -0.3%] | -2.4% [-3.0%, -2.0%] |
| fallback_domain | 3.163 | 1.617 | 1.596 | +0.1% [-0.1%, +0.3%] | +0.1% [-0.2%, +0.3%] | -1.4% [-1.8%, -1.0%] |
| best_domain | 3.165 | 1.623 | 1.602 | +0.5% [+0.3%, +0.7%] | +0.4% [+0.3%, +0.6%] | -0.8% [-1.1%, -0.7%] |

Walk con gate sul match (match≥12, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)

| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |
|---|---|---|---|---|---|---|
| lookup | 2.532 | 1.569 | 1.553 | — | — | — |
| pool_domain | 2.554 | 1.564 | 1.548 | -0.3% [-0.5%, -0.2%] | -0.3% [-0.5%, -0.2%] | -1.1% [-1.4%, -0.8%] |
| fallback_domain | 2.537 | 1.568 | 1.552 | -0.0% [-0.1%, +0.0%] | -0.0% [-0.1%, +0.0%] | -0.1% [-0.3%, -0.1%] |
| best_domain | 2.538 | 1.569 | 1.554 | +0.0% [-0.0%, +0.1%] | +0.0% [-0.0%, +0.1%] | -0.1% [-0.2%, -0.0%] |

Speedup stimato assoluto (K=7) N·s(1)/ΣT_round: lookup: P1 1.534, P2 1.511, B-flat 3.635, B-lin 0.776; pool_domain: P1 1.449, P2 1.425, B-flat 3.791, B-lin 0.708

P(a≥j | T>j), lookup, j=1..7: 0.84 0.77 0.73 0.70 0.67 0.66 0.64
P(a≥j | T>j), pool_domain, j=1..7: 0.78 0.70 0.66 0.62 0.59 0.58 0.56

P(a≥1 | match bucket) [n]: lookup: m3: 0.46 [2931], m4: 0.72 [5318], m8: 0.90 [4238], m16: 0.99 [25442]; pool_domain: m3: 0.41 [3387], m4: 0.69 [5579], m8: 0.87 [4789], m16: 0.99 [25505]

## Dominio `session_full` — 387 richieste, 114 cluster, 305414 token di y, sorgenti: strata-git

| sorgente | copertura (pos. con proposta) | P(a≥1 \| proposta) | acc. media \| proposta | AL K=5 | AL K=7 | righe sprecate M4 (K=7) |
|---|---|---|---|---|---|---|
| lookup | 75.7% | 80.6% | 4.33 | 2.229 | 2.374 | 53.4% |
| pool_domain | 86.2% | 77.8% | 4.18 | 2.556 | 2.769 | 59.0% |
| fallback_domain | 86.2% | 77.5% | 4.13 | 2.548 | 2.761 | 59.2% |
| best_domain | 81.4% | 82.4% | 4.43 | 2.558 | 2.771 | 50.6% |
| pool_session | 80.0% | 81.2% | 4.42 | 2.425 | 2.612 | 51.6% |
| fallback_session | 80.0% | 80.8% | 4.38 | 2.419 | 2.605 | 51.9% |
| best_session | 79.3% | 81.9% | 4.46 | 2.425 | 2.613 | 50.4% |

Guadagno relativo vs lookup per richiesta (IC95), K=7: AL e speedup stimato = N·s(1)/ΣT_round

| sorgente | ΔAL | Δspeedup P1 | Δspeedup P2 | Δspeedup B-flat | Δspeedup B-lin |
|---|---|---|---|---|---|
| pool_domain | +16.6% [+12.4%, +21.8%] | -6.0% [-8.4%, -3.9%] | -6.3% [-8.5%, -3.8%] | +16.5% [+12.1%, +21.6%] | -13.3% [-15.8%, -11.1%] |
| fallback_domain | +16.3% [+11.8%, +21.3%] | -6.4% [-8.5%, -4.2%] | -6.6% [-8.9%, -4.4%] | +16.2% [+11.5%, +21.0%] | -13.6% [-15.9%, -11.6%] |
| best_domain | +16.7% [+11.8%, +21.9%] | +4.9% [+2.9%, +7.3%] | +4.8% [+2.7%, +7.2%] | +16.7% [+12.0%, +21.8%] | +0.6% [-0.8%, +2.0%] |
| pool_session | +10.0% [+5.9%, +14.9%] | +3.1% [+1.1%, +5.4%] | +3.0% [+1.1%, +5.2%] | +10.0% [+6.0%, +14.8%] | +0.4% [-0.8%, +1.8%] |
| fallback_session | +9.8% [+5.7%, +14.4%] | +2.7% [+0.9%, +4.6%] | +2.6% [+0.9%, +4.5%] | +9.7% [+5.6%, +14.5%] | -0.1% [-1.1%, +1.0%] |
| best_session | +10.1% [+6.0%, +14.7%] | +4.5% [+2.3%, +6.9%] | +4.4% [+2.4%, +6.8%] | +10.0% [+5.8%, +14.7%] | +2.3% [+0.9%, +3.7%] |

Walk con gate sul match (match≥6, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)

| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |
|---|---|---|---|---|---|---|
| lookup | 1.908 | 1.283 | 1.272 | — | — | — |
| pool_domain | 2.137 | 1.323 | 1.309 | +3.1% [+1.4%, +4.9%] | +2.9% [+1.3%, +4.7%] | -2.6% [-3.2%, -2.1%] |
| fallback_domain | 2.120 | 1.317 | 1.304 | +2.7% [+1.1%, +4.3%] | +2.5% [+1.1%, +4.2%] | -2.7% [-3.3%, -2.3%] |
| best_domain | 2.131 | 1.336 | 1.323 | +4.2% [+2.5%, +6.0%] | +4.0% [+2.4%, +5.9%] | -0.7% [-1.1%, -0.5%] |
| pool_session | 2.082 | 1.327 | 1.314 | +3.4% [+1.8%, +5.3%] | +3.3% [+1.7%, +5.1%] | -0.4% [-0.6%, -0.1%] |
| fallback_session | 2.069 | 1.322 | 1.309 | +3.0% [+1.6%, +4.7%] | +2.9% [+1.5%, +4.6%] | -0.6% [-0.8%, -0.4%] |
| best_session | 2.078 | 1.329 | 1.316 | +3.6% [+1.8%, +5.4%] | +3.5% [+1.8%, +5.5%] | -0.0% [-0.2%, +0.2%] |

Walk con gate sul match (match≥12, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)

| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |
|---|---|---|---|---|---|---|
| lookup | 1.579 | 1.257 | 1.250 | — | — | — |
| pool_domain | 1.731 | 1.304 | 1.295 | +3.7% [+2.1%, +5.5%] | +3.6% [+2.0%, +5.4%] | -1.7% [-2.0%, -1.4%] |
| fallback_domain | 1.710 | 1.296 | 1.287 | +3.1% [+1.6%, +4.7%] | +3.0% [+1.5%, +4.6%] | -1.7% [-2.0%, -1.5%] |
| best_domain | 1.721 | 1.306 | 1.297 | +3.9% [+2.3%, +5.7%] | +3.8% [+2.1%, +5.6%] | -0.8% [-1.0%, -0.7%] |
| pool_session | 1.707 | 1.302 | 1.294 | +3.6% [+1.9%, +5.4%] | +3.5% [+1.9%, +5.3%] | -0.6% [-0.8%, -0.5%] |
| fallback_session | 1.689 | 1.295 | 1.287 | +3.0% [+1.5%, +4.7%] | +2.9% [+1.5%, +4.6%] | -0.7% [-0.9%, -0.6%] |
| best_session | 1.698 | 1.300 | 1.292 | +3.4% [+1.9%, +5.2%] | +3.3% [+1.7%, +5.1%] | -0.4% [-0.5%, -0.3%] |

Speedup stimato assoluto (K=7) N·s(1)/ΣT_round: lookup: P1 1.131, P2 1.115, B-flat 2.365, B-lin 0.600; pool_domain: P1 1.062, P2 1.045, B-flat 2.756, B-lin 0.521

P(a≥j | T>j), lookup, j=1..7: 0.68 0.56 0.48 0.43 0.39 0.37 0.35
P(a≥j | T>j), pool_domain, j=1..7: 0.61 0.49 0.42 0.37 0.35 0.32 0.31

P(a≥1 | match bucket) [n]: lookup: m3: 0.49 [36177], m4: 0.69 [58496], m8: 0.86 [38143], m16: 0.97 [98360]; pool_domain: m3: 0.43 [46478], m4: 0.65 [64912], m8: 0.86 [38536], m16: 0.97 [113283]

## Dominio `session_excerpt` — 387 richieste, 114 cluster, 305414 token di y, sorgenti: strata-git

| sorgente | copertura (pos. con proposta) | P(a≥1 \| proposta) | acc. media \| proposta | AL K=5 | AL K=7 | righe sprecate M4 (K=7) |
|---|---|---|---|---|---|---|
| lookup | 66.6% | 85.6% | 4.87 | 2.006 | 2.109 | 46.2% |
| pool_domain | 81.1% | 81.9% | 4.59 | 2.425 | 2.602 | 54.7% |
| fallback_domain | 81.1% | 81.5% | 4.54 | 2.419 | 2.596 | 55.0% |
| best_domain | 75.7% | 87.9% | 4.93 | 2.429 | 2.606 | 43.4% |
| pool_session | 74.8% | 85.3% | 4.88 | 2.285 | 2.438 | 46.6% |
| fallback_session | 74.8% | 84.9% | 4.82 | 2.280 | 2.432 | 47.0% |
| best_session | 73.1% | 87.4% | 5.00 | 2.287 | 2.439 | 42.6% |

Guadagno relativo vs lookup per richiesta (IC95), K=7: AL e speedup stimato = N·s(1)/ΣT_round

| sorgente | ΔAL | Δspeedup P1 | Δspeedup P2 | Δspeedup B-flat | Δspeedup B-lin |
|---|---|---|---|---|---|
| pool_domain | +23.4% [+19.0%, +27.6%] | -5.9% [-7.6%, -4.1%] | -6.2% [-7.9%, -4.5%] | +23.2% [+18.7%, +27.5%] | -16.8% [-18.7%, -14.6%] |
| fallback_domain | +23.1% [+19.1%, +27.5%] | -6.2% [-7.8%, -4.6%] | -6.6% [-8.1%, -4.9%] | +22.9% [+18.7%, +27.4%] | -17.1% [-19.0%, -15.0%] |
| best_domain | +23.6% [+19.6%, +27.9%] | +6.2% [+4.5%, +8.0%] | +6.0% [+4.3%, +7.7%] | +23.5% [+19.3%, +27.8%] | -1.4% [-2.4%, -0.6%] |
| pool_session | +15.6% [+11.0%, +20.0%] | +2.0% [+0.8%, +3.5%] | +1.9% [+0.5%, +3.3%] | +15.5% [+11.4%, +19.5%] | -4.1% [-5.4%, -2.5%] |
| fallback_session | +15.3% [+11.2%, +19.4%] | +1.7% [+0.5%, +3.0%] | +1.5% [+0.4%, +2.8%] | +15.3% [+11.1%, +19.5%] | -4.6% [-5.8%, -3.0%] |
| best_session | +15.7% [+11.5%, +19.9%] | +5.8% [+4.0%, +7.6%] | +5.6% [+3.9%, +7.3%] | +15.6% [+11.4%, +19.9%] | +1.0% [+0.3%, +1.7%] |

Walk con gate sul match (match≥6, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)

| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |
|---|---|---|---|---|---|---|
| lookup | 1.790 | 1.284 | 1.275 | — | — | — |
| pool_domain | 2.079 | 1.332 | 1.319 | +3.7% [+2.3%, +5.1%] | +3.5% [+2.2%, +4.8%] | -4.7% [-5.5%, -4.0%] |
| fallback_domain | 2.062 | 1.327 | 1.315 | +3.3% [+2.1%, +4.6%] | +3.1% [+1.9%, +4.4%] | -4.7% [-5.5%, -4.1%] |
| best_domain | 2.074 | 1.353 | 1.340 | +5.4% [+3.9%, +6.8%] | +5.2% [+3.7%, +6.6%] | -1.9% [-2.5%, -1.5%] |
| pool_session | 2.015 | 1.338 | 1.326 | +4.2% [+2.8%, +5.7%] | +4.0% [+2.7%, +5.4%] | -1.8% [-2.2%, -1.3%] |
| fallback_session | 2.001 | 1.333 | 1.321 | +3.8% [+2.5%, +5.1%] | +3.7% [+2.4%, +4.9%] | -1.9% [-2.3%, -1.5%] |
| best_session | 2.011 | 1.346 | 1.334 | +4.8% [+3.2%, +6.3%] | +4.6% [+3.2%, +6.2%] | -0.7% [-0.9%, -0.4%] |

Walk con gate sul match (match≥12, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)

| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |
|---|---|---|---|---|---|---|
| lookup | 1.548 | 1.253 | 1.247 | — | — | — |
| pool_domain | 1.729 | 1.308 | 1.300 | +4.4% [+3.0%, +5.9%] | +4.2% [+2.8%, +5.7%] | -2.3% [-2.7%, -2.0%] |
| fallback_domain | 1.705 | 1.300 | 1.291 | +3.7% [+2.4%, +5.0%] | +3.6% [+2.3%, +4.9%] | -2.3% [-2.6%, -2.0%] |
| best_domain | 1.716 | 1.311 | 1.303 | +4.6% [+3.3%, +6.1%] | +4.5% [+3.1%, +5.9%] | -1.1% [-1.3%, -0.9%] |
| pool_session | 1.703 | 1.307 | 1.299 | +4.3% [+2.8%, +5.9%] | +4.2% [+2.6%, +5.7%] | -1.1% [-1.2%, -0.8%] |
| fallback_session | 1.681 | 1.299 | 1.291 | +3.6% [+2.3%, +5.0%] | +3.5% [+2.2%, +4.8%] | -1.1% [-1.3%, -0.9%] |
| best_session | 1.691 | 1.306 | 1.298 | +4.2% [+2.7%, +5.6%] | +4.1% [+2.6%, +5.6%] | -0.6% [-0.7%, -0.5%] |

Speedup stimato assoluto (K=7) N·s(1)/ΣT_round: lookup: P1 1.193, P2 1.179, B-flat 2.103, B-lin 0.688; pool_domain: P1 1.122, P2 1.105, B-flat 2.592, B-lin 0.573

P(a≥j | T>j), lookup, j=1..7: 0.74 0.62 0.55 0.50 0.47 0.45 0.43
P(a≥j | T>j), pool_domain, j=1..7: 0.65 0.53 0.46 0.42 0.39 0.37 0.35

P(a≥1 | match bucket) [n]: lookup: m3: 0.54 [24221], m4: 0.73 [43215], m8: 0.88 [32569], m16: 0.98 [103487]; pool_domain: m3: 0.46 [35362], m4: 0.67 [53195], m8: 0.88 [36141], m16: 0.97 [122843]

## Memoria del pool

SuffixDrafter: tabella = next_pow2(2·capacità) slot × 32 B (+4 B/token di storia). Per avere la stessa qualità serve capacità ≥ storia; a tabella piena i nuovi trigrammi non vengono più indicizzati (find_slot → nullptr, suffix_drafter.cpp:48) → un pool reale ha bisogno di eviction (finestra o LRU per richiesta, come `max_cached_requests` di SuffixDecoding).

| pool | token di storia | MiB con capacità = storia |
|---|---|---|
| domain:session_full | 6471108 | 536.7 |
| session:full:strata_cli/launch/runner.py | 792682 | 67.0 |
| session:full:CMakeLists.txt | 749726 | 66.9 |
| domain:session_excerpt | 515335 | 34.0 |
| session:full:src/dsv41/ds4_main.cpp | 415790 | 33.6 |
| session:full:src/dsv41/ds4_iq.cu | 375340 | 33.4 |

Riferimento: llama.cpp ngram-mod ≈16 MB (piano v2). Con la struttura attuale 16 MiB corrispondono a ~246k token di storia (≈64 B/slot effettivi a carico 0,5).
