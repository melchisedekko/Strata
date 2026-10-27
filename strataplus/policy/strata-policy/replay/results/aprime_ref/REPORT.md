# Riferimento del replay di Strata Policy per la soglia (i) del run (a') v3
proxy CPU, non AMD, llama.cpp non Strata. Replay TF su holdout_tf_d7 (cap 3 per troncamento), non una misura live. Orari CET (UTC+1).

**Questo file e' sincronizzato: niente numeri del dominio edit.** Gli aggregati edit sono in `REPORT_<ET>.md` e nel riferimento `aprime_ref_AL_<ET>.json` (file con tag, esclusi dalla sincronizzazione). I dettagli per prompt sono solo in `/workspace/policy-local/aprime_ref/`.

## Numeri aggregati (code, chat)
| dominio | prompt | round verify | AL somma/somma (riferimento) | info: senza first_window | info: media per prompt | first_window | vince mtp | vince lookup | gate vero | gate vero ma mtp | gate falso | round coda cap<3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| code | 30 | 784 | 4.548469 | 4.689655 | 4.679790 | 30 | 548 (72.7%) | 206 (27.3%) | 551 | 345 | 203 | 17 |
| chat | 30 | 1340 | 2.715672 | 2.754962 | 2.819617 | 30 | 1274 (97.3%) | 36 (2.7%) | 93 | 57 | 1217 | 25 |

Istogramma (sorgente:T) - code: first_window:T1=30, lookup:T2=1, lookup:T3=2, lookup:T4=10, lookup:T5=10, lookup:T6=1, lookup:T7=2, lookup:T8=180, mtp:T1=5, mtp:T2=4, mtp:T3=5, mtp:T4=534
Istogramma (sorgente:T) - chat: first_window:T1=30, lookup:T3=8, lookup:T4=7, lookup:T5=3, lookup:T6=13, lookup:T8=5, mtp:T1=6, mtp:T2=11, mtp:T3=8, mtp:T4=1249

Bozze - code: mtp: 548 bozze, 1616 token in bozza, 1488 accettati; lookup: 206 bozze, 1352 token in bozza, 1301 accettati. Chat: mtp: 1274 bozze, 3774 token in bozza, 2191 accettati; lookup: 36 bozze, 149 token in bozza, 110 accettati.

Riferimento per Bench: `POLICY_REPLAY_REF=/workspace/strata-policy/replay/results/aprime_ref/aprime_ref_AL_<ET>.json`, `POLICY_REPLAY_REF_SHA256=cfc9da837c6cd7de48fd31f0f6f13badda40f5d433e14e98afc9937ba8d3d003`. Il JSON ha `AL` = {code, edit, chat}; decide usa code ed edit, chat compare solo in `al_dev_vs_replay` e non cambia il verdetto (aprime_toks_ab.py L77-79).

## Coerenza e copertura
- 30 prompt per dominio, tutti percorsi fino a EOG o n_predict=128; un first_window per prompt.
- Code: vince mtp nel 72.7% dei round non first_window; il gate (lookup[0] == mtp[0]) e' vero nel 73.1% dei round, e l'arbitro sceglie comunque mtp in 345 di quei 551 casi. Chat: quasi sempre mtp con T=4 (bozza di 3 token); lookup in 36 round.

## Definizione di AL usata
AL per dominio = somma su tutti i round verify (compreso il round first_window, T=1) di `min(accepted+1, committed)` / numero di round verify (somma/somma). `min(accepted+1, committed)` = token accettati + token bonus del target, troncato al primo EOG.
Fonte: `strata-bench/tools/aprime_post.py` L6, L43-45 (`v = min(accepted+1, committed)`), L53 (`sumsum_all`); consumato da `tools/aprime_toks_ab.py decide` L74 (`sumsum_all`), L75-79 (`json.load(POLICY_REPLAY_REF)['AL']`, `dev = AL_live/ref - 1`, `|dev| <= 0.03` su code ed edit). Soglia: `runs/live_combo_aprime_holdout_v3.md` sez. 5 (i), L65.

## Come e' stato calcolato
- Run file pre-registrato (read-only, scritto prima di ogni numero): `/workspace/strata-policy/replay/run_aprime_live_ref_v2.json`, sha256 `672bba2ca0c436872fcd2bc95657da5b8d584fef5c4613700595c0098fdea1ac`. Sostituisce `run_aprime_live_ref.json` (sha256 `1e139df78b10969b7278f65eba51bfd32f6021c7982e81ea76ccc52c3c39dc33`): il run v1 si e' fermato con rc=1 su un controllo di sanita' troppo stretto dello script (EOG in ultima posizione), senza produrre numeri; v2 corregge solo quella condizione.
- Script: `replay/aprime_live_ref_v2.py`, sha256 `c811322f58ba368d95c46397ae53010d9995e913f9ba0ac24cb6f8ae7f56d2e6`. Importa l'arbitro di Strata Bench `proxy/strata_arbiter_v1.py` (sha256 `2b0e8b9a...`, nessuna reimplementazione) e rifa' il giro del tracer v14 (L320-455, L482) in modo live sulla traccia `holdout_tf_d7.jsonl` (sha256 `a16cf384...`).
- Braccio (a'): S=8, S_mtp=4, spec_min_p=0, lookup propose(7), MTP cap 3, n_predict 128; s(T) = kShape di default; margine 0.03; probe 3 (q>=0.85); staleness 300; prior kPriorQ/kPriorN; stato azzerato per prompt; round 0 = first_window (T=1, niente choose/observe).
- Accettazione: `lcp(bozza, y[pos:])` con y = output greedy del TF; committed = fino al primo EOG; controllo: token committati = len(y) per ogni prompt (superato su tutti i 90).
- CPU: python, nice 19, 1 processo, 13:41:04 CET (UTC+1), < 1 s; righe in `/workspace/strata-plus/cpu_busy_policy.log`. Nessun processo llama/aprime in corso.

## Limiti
1. **tf_d7 non e' cap 3**: i candidati MTP sono i primi 3 dei 7 token del TF d7 (troncamento). La proprieta' di prefisso non vale al 100%: `mtp_cap_prefix_check.json` all_pairs 5210/5389 = 0.966784 coincidenti, `all_100pct` false. Anche il gate usa `mtp[0]` del TF d7. Un live cap 3 puo' quindi scostarsi da questo riferimento per ragioni non legate all'arbitro.
2. **Proxy**: CPU, non AMD; llama.cpp, non Strata; arbitro = copia di DraftPolicy (v2 md sez. 5). Accettazione ricostruita assumendo il live greedy-identico a y (lo verifica il controllo (ii) di Bench).
3. **Contaminazione irrilevante**: l'AL non dipende dai ms; dalla traccia non si legge nessun tempo.
4. **s(T) parametrica**: fissata al default kShape (nessun profilo misurato); su AMD choose usa l'EMA dei tempi, quindi le scelte di T e di sorgente possono cambiare. Le probabilita' MTP non contano in (a') perche' spec_min_p = 0.
5. Coda: nei round con meno di 3 token rimasti (colonna "round coda cap<3") il cap MTP live si riduce come nel tracer (v14 L330-335).
