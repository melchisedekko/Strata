# Replay lookup-only PRE-REGISTRATO, holdout v1.1: solo AL, descrittivo (proxy CPU 2B, non AMD)

## Riferimenti
- **Run file:** replay/run_lookup_only_replay.json, sha256 584ae02f6a60ed89f6a7cf7268106ebbc9834452f36d0fb46fb2f77eb8e7a40b.
  - Scritto alle 07:06:50 CET, in sola lettura, prima del calcolo.
  - Approvazione Lead delle 07:06 CET.
- **Script:** replay/lookup_only_replay.py.
- **Tracce holdout v1.1** (gli sha coincidono con MANIFEST.sha256):

  | file | sha256 |
  |---|---|
  | code | a9e247b2fd9a0da14517459f028d2b9e85195955895855459c3c924f0e37f603 |
  | chat | b5380c42b9155571054958f00cb501ca7a309feaf8e9cc058f54bd00692b4588 |
  | edit | d9a48386945b1131766cb8b38a1572bc2d3992d8b5bd8291ecbe85c79f3e94ef |

- **Drafter:** strata::spec::SuffixDrafter(min_match=3, max_match=64), con propose(max_k=dmax).
  - È lo stesso drafter rigenerato dei report precedenti: lib 8fb27b0d…, native.py 6bc1af8e…, postprocess.py 02811133….
  - Per ogni braccio si fa uno scan con max_k=dmax.

**Metodo.**
- A ogni round si propone il candidato tagliato a dmax. Se non c'è candidato, il round produce 1 token senza draft.
- Accettazione: a = min(lcp(cand[:dmax], y[p:p+dmax]), n−p−1).
- AL = token emessi per round, compreso il token corretto; p avanza di a+1.
- IC95: bootstrap percentile sulle richieste, B=2000, seed 0.

**Controllo con dmax=7.** Candidato tagliato (k e token) e accettazione coincidono con le tracce: **0 discrepanze** su 3566, 3639 e 3752 posizioni (code, chat, edit).

## AL per dominio e braccio (richiesta intera sul riferimento)

| dominio | richieste | dmax 7 | dmax 12 | dmax 16 | round con candidato, 7 / 12 / 16 |
|---|---|---|---|---|---|
| code | 30 | 3,711 [3,126; 4,384] (3566 tok / 961 round) | 4,386 [3,553; 5,425] (3566 tok / 813 round) | 4,704 [3,743; 5,979] (3566 tok / 758 round) | 45,3% / 35,3% / 30,6% |
| chat | 30 | 1,104 [1,058; 1,180] (3639 tok / 3296 round) | 1,105 [1,059; 1,182] (3639 tok / 3293 round) | 1,105 [1,059; 1,182] (3639 tok / 3293 round) | 6,9% / 6,8% / 6,8% |
| edit | 30 | 3,500 [2,815; 4,539] (3752 tok / 1072 round) | 4,105 [3,158; 5,734] (3752 tok / 914 round) | 4,353 [3,284; 6,317] (3752 tok / 862 round) | 46,9% / 37,7% / 34,0% |

## Istogramma delle accettazioni (numero di round)
La colonna "no cand" conta i round senza candidato. Le colonne a=0..dmax contano i round con candidato e accettazione a.

**dmax 7**

| dominio | no cand | a=0 | a=1 | a=2 | a=3 | a=4 | a=5 | a=6 | a=7 |
|---|---|---|---|---|---|---|---|---|---|
| code | 526 | 23 | 30 | 9 | 6 | 6 | 4 | 4 | 353 |
| chat | 3070 | 83 | 62 | 33 | 14 | 8 | 19 | 3 | 4 |
| edit | 569 | 66 | 26 | 20 | 15 | 8 | 16 | 7 | 345 |

**dmax 12**

| dominio | no cand | a=0 | a=1 | a=2 | a=3 | a=4 | a=5 | a=6 | a=7 | a=8 | a=9 | a=10 | a=11 | a=12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| code | 526 | 21 | 17 | 8 | 5 | 7 | 5 | 0 | 3 | 3 | 1 | 2 | 2 | 213 |
| chat | 3070 | 80 | 62 | 33 | 14 | 8 | 19 | 3 | 1 | 3 | 0 | 0 | 0 | 0 |
| edit | 569 | 57 | 16 | 11 | 11 | 5 | 7 | 8 | 6 | 9 | 6 | 4 | 4 | 201 |

**dmax 16**

| dominio | no cand | a=0 | a=1 | a=2 | a=3 | a=4 | a=5 | a=6 | a=7 | a=8 | a=9 | a=10 | a=11 | a=12 | a=13 | a=14 | a=15 | a=16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| code | 526 | 13 | 21 | 12 | 3 | 6 | 1 | 0 | 2 | 1 | 2 | 3 | 3 | 2 | 1 | 3 | 1 | 158 |
| chat | 3070 | 80 | 62 | 33 | 14 | 8 | 19 | 3 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| edit | 569 | 51 | 21 | 13 | 8 | 6 | 6 | 13 | 2 | 1 | 3 | 5 | 3 | 1 | 4 | 2 | 1 | 153 |

## Come leggeremo il confronto con la run live di Bench (pre-registrato)
- **Prefisso comune.** Il replay va confrontato con l'AL live sul PREFISSO COMUNE con il riferimento. Dopo la prima divergenza la traiettoria live non è più il riferimento teacher-forced.
- **Criterio descrittivo.** Per ogni dominio e braccio si riporta (AL live sul prefisso comune − AL replay)/AL replay, in %. Non è un test go/no-go.
- **Dati per richiesta.** Il json contiene, per ogni richiesta, n, round e round con candidato.
  - Restringere il replay al prefisso comune richiede i dati live: per ora non è calcolato.

## Limiti
- Proxy llama.cpp 2B ("proxy CPU, non AMD"), con uscite di al massimo 128 token.
- In code ed edit c'è molta copia dal prompt.
- Il replay usa il riferimento greedy intero.
- Solo AL, nessun tok/s.
- Non è stato calcolato altro.
