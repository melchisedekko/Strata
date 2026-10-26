# strataplus-HFC-frozen-v1 — tabella s(T) congelata in DraftPolicy (H-FC)

- Base: Strata `7dd5cf1` (MIT). Patch: `strataplus-HFC-frozen-v1.patch`, sha256 `4ab7632926bf117e4a721c41e266c01de691b2eb51bd8ac68e1508060e344433` (464 righe, `git apply` su 7dd5cf1).
- Specifica: `/workspace/strata-plus/scout_spec_HFC_v2.md` (sha256 72a4b134…), Addendum A incluso.
- Solo lato host (DraftPolicy + generate.cpp). Nessun kernel, nessun .cu/HIP.

## Cosa fa
- `DraftPolicy`: flag `frozen_` (default false) con `set_frozen(bool)`, `frozen()`, `set_costs(ms, n, bucket, n_eff = 1000)`.
  Con frozen attivo:
  - `observe`/`observe_chain`: il ramo EMA diventa `round_ms > 0 && !frozen_`; il nuovo `else if (round_ms > 0)` aggiorna solo `last_`. `cost_`/`cost_n_` restano fermi e `clamp_sample` non viene chiamato.
  - `stale()` restituisce false, quindi niente re-probe ogni 300 round. Con n = 1000 ≥ kProbes non partono nemmeno i probe dei T «non misurati».
  - `set_context()` cambia solo `bk_`, anche senza robust, e non copia nulla tra bucket.
  - acceptance (`ok_/bad_`, `cok_/cbad_`), `mtp_tok_/mtp_n_` e `observe_probs` sono invariati.
- `STRATA_SPEC_COST_FROZEN=<path di un file>`, letto in CLI (`strata generate`) e in serve. Funziona con o senza `STRATA_SPEC_COST`.
- A fine run CLI, la riga `spec cost table` esce anche con frozen (`if (spec_cost || policy.frozen())`, §2(d) della specifica, opzionale). Serve a verificare che la tabella non si sia mossa.
- Senza l'env, il comportamento è identico a 7dd5cf1: tutti i rami nuovi sono protetti da `frozen_`, e la riga di report resta `spec_cost`.

## Uso
File di testo con **3 liste separate da `;`**, nell'ordine bucket ctx<6K, ctx<24K, ctx>=24K. In ogni lista ci sono i ms/round di T1..Tn separati da `,`. È il formato di `STRATA_SPEC_COST_TABLE`, con `atof`, al più 8 valori per lista e liste oltre la terza ignorate. Gli a capo dopo `;` o in fondo sono ammessi.
```
s1,s2,s3,s4,s5,s6,s7,s8;
s1,s2,s3,s4,s5,s6,s7,s8;
s1,s2,s3,s4,s5,s6,s7,s8
```
`STRATA_SPEC_COST_FROZEN=/percorso/tabella.txt strata generate … --spec 8 …`
- Errore e uscita (`return 1` da main) nei casi seguenti; in tutti questi casi la policy non viene toccata:
  - file non apribile;
  - meno di 3 liste;
  - in un bucket manca un T tra 1 e min(--spec, 8), oppure vale ≤ 0 (campo vuoto o non numerico → 0).
- All'avvio, su stderr: `strata: costo congelato (STRATA_SPEC_COST_FROZEN): file <path> sha256 <hex>` e poi la stessa etichetta con `cost_table_text()`.
- La calibrazione (T_CYCLE) va fatta **senza** questo env (specifica §3/§4).

## File e righe (numstat vs 7dd5cf1; righe in coordinate 7dd5cf1)
| file | +/− | dove |
|---|---|---|
| include/strata/spec/draft_policy.hpp | +8/−0 | dopo `set_robust` (L60): set_frozen/frozen/set_costs; `frozen_` dopo `robust_` (L94) |
| src/spec/draft_policy.cpp | +21/−4 | `set_costs` dopo seed_costs (L74); set_context L77/L79; stale L116; observe L156-162; observe_chain L260-266 |
| src/program/generate.cpp | +19/−1 | include L88; helper `load_frozen_costs` nel namespace anonimo (L153); serve dopo L11182; CLI dopo L16447; report L16745 |
| include/strata/spec/frozen_costs.hpp (nuovo) | +115 | sha256 (FIPS 180-4), parser/validazione `apply_frozen_costs_text`, `load_frozen_costs_file` |
| src/spec/draft_policy_frozen_test.cpp (nuovo) | +167 | test unitario (32 controlli) |
| CMakeLists.txt | +4/−0 | target/test `draft_policy_frozen_test` dopo draft_policy_test (L1552) |

## Testato (box CPU, g++ 14.2, cmake 3.31 + ninja; `nice -n 19`, `-j2`)
- Build minimale `/workspace/scout-local/hfc_build`: `-DSTRATA_NATIVE_EXPERTS=OFF -DSTRATA_BUILD_TESTS=ON`, solo i target `strata_spec`, `draft_policy_test` e `draft_policy_frozen_test`. rc=0.
- `draft_policy_frozen_test`: PASS (32/32), rc=0. Cosa copre:
  - frozen spento: l'EMA si muove e i probe stale partono (controllo di sensibilità);
  - frozen acceso: la tabella resta ferma dopo 4000 observe/observe_chain con round_ms > 0;
  - stale falso, nessun probe stale in choose/chain, nessun probe kProbes in keep_draft;
  - last_ aggiornato (verificato sbloccando il flag dopo);
  - l'acceptance e observe_probs imparano ancora;
  - set_context senza copie;
  - loader: rifiuta 0/1/2 bucket, T mancante, valore 0, campo vuoto, non numerico, --spec > n, file inesistente; accetta una tabella completa;
  - sha256 sui vettori noti.
- `draft_policy_test` originale: PASS, rc=0.
- Identità con 7dd5cf1, frozen spento: un driver (fuori patch) esegue 4 configurazioni (robust on/off × seed on/off). Ognuna fa 20000 round pseudo-casuali di set_context/choose/chain/keep_draft/observe/observe_chain/observe_probs. Il driver è stato compilato contro la DraftPolicy di 7dd5cf1 (`git show`) e contro quella patchata. Le uscite (80088 righe) sono identiche byte per byte (`cmp` rc=0, sha256 d31fbf9a… per entrambe).
- Aggancio CLI: la funzione `load_frozen_costs` è stata estratta così com'è dal generate.cpp patchato e la riga di aggancio CLI è stata copiata in un main di prova. Esiti:
  - senza env: rc=0;
  - file valido: rc=0, sha256 uguale a `sha256sum`;
  - file con 2 bucket, con T mancante o inesistente: rc=1 con messaggio.
- `git apply --check` su 7dd5cf1: rc=0. Applicata in un worktree temporaneo, dà file identici al worktree di lavoro.
- `git apply --check` su `b24c6a1` (main del fork, 164 commit dopo 7dd5cf1): rc=0, solo offset. Lì `draft_policy_frozen_test` compilato con g++ passa.

## Non testato
- **Il binario `strata` non è stato compilato.** Il target `strata` (generate.cpp) esiste solo con CUDA/HIP (CMakeLists `if(STRATA_ENABLE_CUDA OR STRATA_ENABLE_HIP)`) e generate.cpp include `cuda_runtime.h`. Su questo box (senza HIP/CUDA) non è compilabile. Le 3 righe di aggancio e l'helper sono verificati solo tramite l'estrazione descritta sopra.
- Il comportamento runtime di `strata generate`/`serve` con l'env non è stato provato, perché servirebbero un modello e una GPU. L'errore all'avvio scatta dove la specifica mette l'aggancio, cioè alla preparazione del ciclo spec: con ogni probabilità dopo il caricamento del modello (non verificato).
- Identità greedy dell'output sul modello e A/B tok/s EMA vs frozen: restano a Strata Bench su AMD.
- Albero `sycl/`:
  - non ha una copia di DraftPolicy: `sycl/CMakeLists.txt` risolve `src/spec/draft_policy.cpp` sulla radice (`strata_resolve`), quindi riceve le modifiche alla classe, inerti perché frozen_ resta false;
  - ha però un proprio `sycl/src/program/generate.cpp`, **non patchato**, quindi l'env lì viene ignorato;
  - nessuna build SYCL.
