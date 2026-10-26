# H-CA — configurazione dello speculative decoding in base al contenuto: valutazione replay (fase 2)

**PROXY CPU**: tracce teacher-forced v1.1 (Qwen3.5-2B-MTP Q4_K_M, llama.cpp + patch draft-mtp-probs), NON Qwen3.8-Flash-Next e non AMD.
**tok/s STIMATI**, non misurati: costo di un round s(T) = 1 + ρ(T−1) in passi a T=1, draft (MTP e lookup) a costo zero; tok/s = Σ token / Σ s(T) (unità: token per passo T=1); AL = Σ token / Σ round (somma su somma). Arbitro: DraftPolicy nativo di 7dd5cf18, policy nuova per richiesta.
Solo aggregati per dominio (licenza: nessun ID, token, testo, linguaggio dei fence; nessuna configurazione stimata — vedi `edit_np_fitted/`, escluso dalla pubblicazione).

## Protocollo e hash
| file | sha256 |
|---|---|
| replay/run_hca.json | ea2bed9c1438175c279c291652a6e9dd552e14b24d694320befc9338249bf50b |
| replay/run_hca_addendum1.json (lettura cross-fitted, verdetti per ρ; scritto prima di eval) | c3490e220313ec377e0fbc0f63f0994a228d351d0286b9248ec125a81726c386 |
| replay/run_hca_addendum2.json (regola edit_np sugli output; scritto DOPO eval, solo separazione dei file) | 4ac1f236b7bf500760fa444d0c7f34e3810700b5f21236fc419389173fc60e49 |
| replay/hca.py (funzioni riusate) | 35ddc537b0306780ceb3d920476d64d1530eec097a55a53f5b3aacbf928ed348 |
| replay/hca_v2.py (eval) | 4f24bba56ac734288ae1af3242c7b3ca09386ce3ca602382fe0ed354ad978ef6 |
| replay/hca_split.py (separazione output) | 81105c9d3c5663a31623b76e962d18b1fda1381097c16d17a071afc834f97230 |
| results/v2/hca/hca_results.json (pubblicabile) | 5e4974c0172a1f9307441b6e93cb7f2054200ecfd46b98f3269c64f7bcf5f413 |
| traces/v1.1 MANIFEST.sha256 | 34bdc195a1ec18824cc5497f4e2c98ef138803672f651cc4db2c045901f68d3f |
| tune tf_d7_p30.jsonl | 87efe507324b2a79b89c21a6736f1478094bf53385d9471694dc71b291d9abfa |
| holdout code / chat / edit (tf_d7) | a9e247b2… / b5380c42… / d9a48386… (sha completi in hca_results.json) |

Esecuzione: 2026-10-26 19:42:20–19:44:15 CET, nice -n 19, OMP/OPENBLAS/MKL_NUM_THREADS=1, rc=0.

## Bracci
- **(1) cf**: una configurazione fissa della griglia (168: S≤8, S_mtp≤S, regola di T fissa/min_p/spec_cost), scelta sulle 4 fold di training, valutata sulla fold esclusa.
- **(2c) cf**: versione causale di (2): una configurazione fissa per **dominio** della richiesta, scelta sulle fold di training.
- **(3c) cf**: versione causale di (3): tabella (dominio, dentro/fuori dal blocco ```) → configurazione, cambio ai confini fence, ascesa per coordinate sul training.
- **cls cf**: classificatore causale a 16 celle (dentro codice, fence nel prompt, tasso di match del lookup sugli ultimi 8 round, fiducia MTP), con base, azioni, soglie e tabella scelte solo sul training.
- **Tetti in-sample**: (2) oracolo per richiesta, (3) oracolo greedy per segmento, e i bracci sopra selezionati sull'intero tune; **oracolo per round** R01 (T≤8, lookup≤7), +P (T≤12, lookup≤11), +X (lookup≤15).
- Le configurazioni scelte (anche quella del braccio (1)) sono artefatti stimati su dati che includono edit: non riportate qui.

## Conteggi
Richieste tune per dominio × fold (fold = indice mod 5): code 2/2/2/2/2, chat 2/2/2/2/2, edit 2/2/2/2/2 (10 per dominio; training 8 per dominio). Holdout v1.1: 30 richieste per dominio (code, chat, edit).

## Verdetti (tune, cross-fitted, insieme di switch R0∪R1; criteri invariati)
| criterio | flat ρ=0.19617814763445762 | steep ρ=0.538461538461537 | combinato |
|---|---|---|---|
| H-CA: (2c) supera (1) di ≥3% in almeno un dominio? | **scende** (nessun dominio ≥3%: code −0.42%, chat −0.16%, edit −0.51%) | **regge** (solo edit +3.16%, IC95 [+0.94%, +5.80%]; code +1.00%, chat −0.24%) | **dipende dall'hardware** |
| classificatore: cattura ≥50% del guadagno di (2c) su (1)? | non applicabile (H-CA scesa) | **NO-GO** (edit: cattura 0.146) | regola meccanica dell'addendum 1: "dipende dall'hardware" (ma il classificatore non è GO in nessuno dei due scenari) |


### Scenario flat (ρ = 0.19617814763445762)

**Tune, lettura decisionale cross-fitted (5 fold)** — tok/s stimati (unità: token per passo T=1) / AL

| dominio | (1) cf | (2c) cf | (3c) cf | cls cf | g(2c) vs (1) [IC95] | g(3c) [IC95] | g(cls) [IC95] | cattura cls su 2c |
|---|---|---|---|---|---|---|---|---|
| code | 2.8515 / 6.045 | 2.8396 / 5.985 | 2.9510 / 6.230 | 2.9369 / 6.198 | -0.42% [-2.04%, +1.12%] | +3.49% [+1.81%, +5.56%] | +3.00% [+0.67%, +5.60%] | n/a (g<3%) |
| chat | 1.7400 / 2.372 | 1.7372 / 2.381 | 1.7082 / 2.349 | 1.6984 / 2.293 | -0.16% [-0.71%, +0.32%] | -1.83% [-3.95%, -0.25%] | -2.39% [-4.90%, -0.56%] | n/a (g<3%) |
| edit | 2.6618 / 5.141 | 2.6483 / 4.848 | 2.6495 / 4.867 | 2.6785 / 5.203 | -0.51% [-3.57%, +2.93%] | -0.46% [-3.11%, +2.80%] | +0.63% [-1.20%, +2.52%] | n/a (g<3%) |

**Tune, in-sample (tetti ottimistici, non decisionali)** — tok/s / AL; guadagni rispetto a (1) cf

| dominio | (1) ins | (2c) ins | (3c) ins | cls ins | (2) oracolo richiesta | (3) oracolo segmento | g oracolo (2) [IC95] |
|---|---|---|---|---|---|---|---|
| code | 2.8837 / 6.167 | 2.9134 / 6.167 | 2.9653 / 6.294 | 2.9584 / 6.326 | 3.0260 / 6.326 | 3.0352 / 6.393 | +6.12% [+3.34%, +9.15%] |
| chat | 1.7436 / 2.395 | 1.7436 / 2.395 | 1.7436 / 2.395 | 1.7541 / 2.381 | 1.7924 / 2.521 | 1.7971 / 2.532 | +3.01% [+1.09%, +5.53%] |
| edit | 2.6798 / 5.246 | 2.7081 / 4.923 | 2.7081 / 4.923 | 2.7330 / 5.333 | 2.8125 / 5.447 | 2.8257 / 5.401 | +5.66% [+3.21%, +8.12%] |

**Oracolo per round (tetto assoluto), tok/s stimati**

| file/dominio | R01 (DP) | R01 greedy | +P (T≤12, lookup≤11) | +X (lookup≤15) | (3) R0-solo |
|---|---|---|---|---|---|
| tune/code | 3.1712 | 3.1646 | 3.4445 | 3.5911 | — |
| tune/chat | 2.1566 | 2.1094 | 2.1597 | 2.1627 | — |
| tune/edit | 3.0366 | 3.0251 | 3.2538 | 3.3925 | — |
| holdout_code/code | 3.2001 | 3.1863 | 3.4923 | 3.6624 | — |
| holdout_chat/chat | 2.3073 | 2.2702 | 2.3073 | 2.3073 | — |
| holdout_edit/edit | 3.1249 | 3.1145 | 3.3807 | 3.5236 | — |

**Holdout v1.1 (solo descrittivo; selezioni dell'intero tune applicate)** — tok/s / AL; guadagni rispetto a (1)

| dominio | (1) | (2c) | (3c) | cls | (2) oracolo | (3) oracolo | g(2c) [IC95] | g(cls) [IC95] | g oracolo (2) [IC95] |
|---|---|---|---|---|---|---|---|---|---|
| code | 2.9937 / 6.460 | 2.9951 / 6.312 | 2.9886 / 6.300 | 2.9660 / 6.245 | 3.0946 / 6.567 | 3.1097 / 6.628 | +0.05% [-1.36%, +1.39%] | -0.93% [-2.17%, +0.24%] | +3.37% [+2.39%, +4.40%] |
| chat | 1.8568 / 2.746 | 1.8568 / 2.746 | 1.8568 / 2.746 | 1.8348 / 2.654 | 1.9170 / 2.832 | 1.9196 / 2.832 | +0.00% [+0.00%, +0.00%] | -1.18% [-2.54%, +0.15%] | +3.24% [+2.22%, +4.42%] |
| edit | 2.8591 / 5.872 | 2.8237 / 5.430 | 2.8237 / 5.430 | 2.8274 / 5.676 | 2.9512 / 6.042 | 2.9472 / 5.946 | -1.24% [-2.89%, +0.30%] | -1.11% [-2.44%, +0.12%] | +3.22% [+2.13%, +4.44%] |

### Scenario steep (ρ = 0.538461538461537)

**Tune, lettura decisionale cross-fitted (5 fold)** — tok/s stimati (unità: token per passo T=1) / AL

| dominio | (1) cf | (2c) cf | (3c) cf | cls cf | g(2c) vs (1) [IC95] | g(3c) [IC95] | g(cls) [IC95] | cattura cls su 2c |
|---|---|---|---|---|---|---|---|---|
| code | 1.5236 / 5.174 | 1.5388 / 5.218 | 1.5388 / 5.218 | 1.5172 / 5.218 | +1.00% [-0.36%, +2.45%] | +1.00% [-0.36%, +2.45%] | -0.42% [-0.83%, -0.01%] | n/a (g<3%) |
| chat | 1.2183 / 1.864 | 1.2154 / 1.896 | 1.2209 / 1.990 | 1.2102 / 1.962 | -0.24% [-1.22%, +0.71%] | +0.21% [-1.28%, +1.84%] | -0.67% [-3.29%, +1.67%] | n/a (g<3%) |
| edit | 1.4741 / 4.414 | 1.5207 / 4.267 | 1.5022 / 4.507 | 1.4810 / 4.588 | +3.16% [+0.94%, +5.80%] | +1.90% [+0.05%, +3.94%] | +0.46% [-1.51%, +2.67%] | 0.1464 |

**Tune, in-sample (tetti ottimistici, non decisionali)** — tok/s / AL; guadagni rispetto a (1) cf

| dominio | (1) ins | (2c) ins | (3c) ins | cls ins | (2) oracolo richiesta | (3) oracolo segmento | g oracolo (2) [IC95] |
|---|---|---|---|---|---|---|---|
| code | 1.5397 / 5.240 | 1.5556 / 5.240 | 1.5638 / 5.286 | 1.5512 / 5.263 | 1.5927 / 5.759 | 1.5959 / 5.787 | +4.54% [+3.23%, +5.87%] |
| chat | 1.2198 / 1.749 | 1.2271 / 2.003 | 1.2321 / 2.010 | 1.2421 / 1.987 | 1.2511 / 2.074 | 1.2596 / 2.138 | +2.69% [+1.68%, +3.87%] |
| edit | 1.5063 / 4.476 | 1.5207 / 4.267 | 1.5207 / 4.267 | 1.5166 / 4.507 | 1.5511 / 4.523 | 1.5581 / 4.776 | +5.22% [+2.81%, +7.83%] |

**Oracolo per round (tetto assoluto), tok/s stimati**

| file/dominio | R01 (DP) | R01 greedy | +P (T≤12, lookup≤11) | +X (lookup≤15) | (3) R0-solo |
|---|---|---|---|---|---|
| tune/code | 1.6478 | 1.6467 | 1.6877 | 1.7073 | 1.5645 |
| tune/chat | 1.4450 | 1.4326 | 1.4457 | 1.4465 | 1.2375 |
| tune/edit | 1.6263 | 1.6244 | 1.6603 | 1.6805 | 1.5206 |
| holdout_code/code | 1.6522 | 1.6501 | 1.6942 | 1.7165 | 1.5886 |
| holdout_chat/chat | 1.4822 | 1.4733 | 1.4822 | 1.4822 | 1.2692 |
| holdout_edit/edit | 1.6405 | 1.6389 | 1.6788 | 1.6984 | 1.5489 |

**Holdout v1.1 (solo descrittivo; selezioni dell'intero tune applicate)** — tok/s / AL; guadagni rispetto a (1)

| dominio | (1) | (2c) | (3c) | cls | (2) oracolo | (3) oracolo | g(2c) [IC95] | g(cls) [IC95] | g oracolo (2) [IC95] |
|---|---|---|---|---|---|---|---|---|---|
| code | 1.5728 / 5.283 | 1.5751 / 5.512 | 1.5729 / 5.503 | 1.5727 / 5.307 | 1.6162 / 5.904 | 1.6232 / 6.065 | +0.14% [-0.70%, +1.08%] | -0.01% [-0.14%, +0.08%] | +2.75% [+1.97%, +3.66%] |
| chat | 1.2512 / 2.002 | 1.2448 / 2.283 | 1.2505 / 2.292 | 1.2549 / 2.345 | 1.2981 / 2.292 | 1.2997 / 2.316 | -0.52% [-2.27%, +1.12%] | +0.30% [-0.81%, +1.47%] | +3.75% [+2.76%, +4.85%] |
| edit | 1.5397 / 4.810 | 1.5399 / 4.702 | 1.5399 / 4.702 | 1.5360 / 4.983 | 1.5854 / 5.314 | 1.5868 / 5.422 | +0.01% [-1.04%, +1.15%] | -0.24% [-1.37%, +1.01%] | +2.97% [+1.98%, +4.06%] |

## Letture e avvertenze
1. **Verdetto H-CA = "dipende dall'hardware"**: con verify economica (flat) nessun dominio passa il 3% con la scelta per dominio; con verify cara (steep) passa solo edit, e di poco (+3.16%, limite inferiore dell'IC +0.94%). Si decide solo sulle misure AMD.
2. **Il criterio usa (2c), che non è un tetto per gli switch dentro la richiesta.** In flat, sul code, gli switch per contenuto superano (1) di ≥3% in cross-fit: (3c) +3.49% [+1.81%, +5.56%] e il classificatore +3.00% [+0.67%, +5.60%], mentre (2c) è −0.42%. Il verdetto "scende" in flat segue la lettera dell'addendum 1 (criterio su (2) vs (1)), ma nel code il segnale "dentro/fuori codice" sembra valere circa il 3% anche con verify economica. In chat (3c) e il classificatore peggiorano (−1.8%, −2.4%, IC sotto zero): c'è sovradattamento con 8 richieste di training per dominio.
3. **La "cattura" del classificatore è poco informativa** quando il guadagno di (2c) è piccolo o negativo (il denominatore cambia segno); conta solo per edit in steep (0.146).
4. **Tetti**: l'oracolo per richiesta supera (1) cf sul tune di +2.69% (chat, steep) fino a +6.12% (code, flat); quello per round (R01) di +8.2% (code, steep) fino a +23.9% (chat, flat); P e X aggiungono margine solo in code ed edit (in chat circa nulla). Sono tetti con conoscenza del futuro, non raggiungibili da una regola causale.
5. **Holdout v1.1 (descrittivo, già usato)**: con le selezioni dell'intero tune, (2c), (3c) e classificatore stanno tra −1.24% e +0.30% rispetto a (1) in tutti i domini e scenari; nessun guadagno di (3c) in code si trasferisce all'holdout (flat −0.17%, steep 0.00%).
6. Campione piccolo (10 richieste tune per dominio, −n 128): IC larghi. Il primo round (first_window T=1) non è modellato, come in sim2.

## Deviazioni
- La regola edit_np (addendum 2) è arrivata dopo l'esecuzione; il calcolo non è stato rifatto. L'output grezzo di eval (contiene configurazioni stimate e conteggi per cella) è rimasto in `results/v2/hca/hca_results.json` dalle 19:44:15 alle 19:45:34 CET, poi è stato spostato senza modifiche in `edit_np_fitted/hca_results_full_edit_np.json`. Il `hca_results.json` attuale è stato rigenerato da `hca_split.py` con una whitelist di chiavi.
- Il combinatore dei verdetti dell'addendum 1 dà "dipende dall'hardware" anche per il classificatore ("non applicabile" in flat contro "NO-GO" in steep): nella sostanza il classificatore non è GO in nessuno scenario.
- Nel log CPU la riga di INIZIO eval ha i campi "(in corso)" e "rc=pending" (non presenti nelle righe esistenti); la riga di FINE è nel formato standard.
- AL e tok/s per fold non sono stati calcolati (non previsti dallo script).
- run_hca.json riga 119 dice che il linguaggio del fence è "registrato nel JSON": non è scritto negli output (licenza) e non entra in nessuna regola.
