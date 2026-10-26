# Replay Strata+ (H1+H4 arbitro, H2 pool) — tutto locale

- `strata_sim/native.py` — ctypes verso il codice REALE: `native/libstrata_spec_capi.so` (DraftPolicy + SuffixDrafter
  @7dd5cf18, non patchati) e `native/libstrata_spec_capi_p3.so` (sorgenti patchati P2+P3+P5: `observe_counterfactual`,
  `set_frozen_costs`, `JointGate`). Il port Python `draft_policy_port.py` serve solo da controllo (`crosscheck/`).
- `strata_sim/sim2.py` — profili di costo (P1/P2 = stime da codice, B-flat/B-lin = limiti, P4 da
  `/workspace/strata-plus/traces/cost_p4_cpu.json` se esiste), walk, oracoli O_round / O_DP / O_depth, policy:
  `strata_current`, `strata_cost` (=STRATA_SPEC_COST=1), `*_cf` (P3), `gate_v2` (candidato principale: un gate per
  sorgente+profondità), `gate_v2_conf` (variante stop su entropia/confidenza, AdaEDL), `gate_v2_pool` (H2),
  `gate_v2_native` (= gate_v2 eseguito dal C++ `JointGate` di P5; parità: `tests/test_joint_gate_parity.py`).
- `run_v2.py --data synthetic|tf:<trace.jsonl> [--grid] --procs 1` → `results/v2/<run>/{summary,grid}.json`;
  `report_v2.py results/v2/<run>` → `report.md` (M1–M5, gap, go/no-go §8, mappa di sensibilità).
- Etichette: ogni output riporta la natura dei dati. `synthetic` = NON è una misura. `tf:` = MTP reale del proxy,
  costi simbolici.

Per avviare il replay su tracce vere servono: righe `strataplus.v1` con `cand.mtp` a Dmax e y (D2/D13);
per P4 il file `cost_p4_cpu.json` (D12). Con nice: `nice -n 19 ../.venv/bin/python run_v2.py --data tf:<path> --procs 1`.

## Varianti v1 nel walk v2 (25/10/2026)
`nice -n 19 python3 run_variants.py --data synthetic|tf:<trace>` → `results/v2/<run>/variants.{md,json}`.
Adattatore `strata_sim/v1adapt.py`: Hedge full-feedback (sto/det, contestuale), stimatore contestuale con/senza bonus
d'accordo, DraftPolicy attuale + full-feedback / split per accordo / senza gate, confrontati con strata_current,
strata_cost e gate_v2 (IC95 bootstrap a cluster). Costo v2 in step × 20 ms (scala del prior v1).

## Parametri congelati (25/10/2026)
- **`frozen_params_v3.json` = file congelato FINALE** (frozen_at 2026-10-25 02:15:32 CET, sola lettura, sha256 `37bf1996217dd4ee697e753b9ef31082c49a9904f0fe393d0c5d4968cf698e9c`). Contiene:
  - commit `051326aa2931e04a9fbdd226f6592cf66e53516e`; diff cumulativo `aed3c0b1…`;
  - P4: 099ceda… fissato dal Lead ed e51712c6… effettivamente usato, equivalenti per il Q4_K_M (confronto in JSON canonico, `cost_derived/p4_q4km_canonical_compare.json`); solo il 2B Q4_K_M, il Q8_0 resta come dato di controllo;
  - V1 (P4 così com'è) e V2 (s(8)=2,7921 da fit ai minimi quadrati su s(1..7));
  - bracci A/B/H e regola.
  **La scelta A vs B NON è decisa: si decide sull'holdout v1.1.**
- `frozen_params_v3_READY_PENDING_P4_CONFIRM.json`: versione pronta prima della conferma del Lead (superata).
- **Decadimento degli hazard MTP rimandato al giro 2 per decisione del Lead:** `../patches/P5x_hazard_decay_ROUND2.diff`, NON applicato. I risultati ottenuti col decadimento sono in `results/v2/_obsolete_decay/` (NON validi).
- `frozen_params_v3_PREPARED_NOT_FROZEN.json` (02:05 CET, sola lettura): **NON VALIDA**, scritta col decadimento.
- `frozen_params_v2.json` (sha256 7b5e484c…) e `frozen_params.json` (v1): intatti, superati.
- `frozen_archive/`:
  - sim2 al congelamento v1;
  - sim2 prima dei fix P5;
  - lib P5 prima dei fix.
  I diff pre-fix sono in `../patches/archive_4e381d7/`.
- Holdout mai aperto: registrati solo gli sha256 dei prompt; `manifest_sha256` = null, da compilare come addendum al manifest v1.1.
- Ambito: gate_v2/P5 vale solo per la sequenza singola (CLI, loop GEN di --serve); il batch (batch_step/BGEN) non chiama DraftPolicy.
