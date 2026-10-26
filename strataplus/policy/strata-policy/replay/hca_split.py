"""H-CA: separa l'output grezzo di eval (edit_np_fitted/hca_results_full_edit_np.json) in
   results/v2/hca/hca_results.json (PUBBLICABILE: whitelist di aggregati per dominio) e
   results/v2/hca/edit_np_fitted/hca_fitted_edit_np.json (artefatti stimati, escluso dal sync).
Regole: run_hca_addendum2.json.  Nessun nuovo calcolo."""
import json, os, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
OUT = os.path.join(HERE, "results/v2/hca"); FULL = os.path.join(OUT, "edit_np_fitted/hca_results_full_edit_np.json")
SH = {"run_hca.json": "ea2bed9c1438175c279c291652a6e9dd552e14b24d694320befc9338249bf50b",
      "run_hca_addendum1.json": "c3490e220313ec377e0fbc0f63f0994a228d351d0286b9248ec125a81726c386",
      "run_hca_addendum2.json": "4ac1f236b7bf500760fa444d0c7f34e3810700b5f21236fc419389173fc60e49",
      "hca_v2.py": "4f24bba56ac734288ae1af3242c7b3ca09386ce3ca602382fe0ed354ad978ef6"}
for f, h in SH.items(): assert sha(os.path.join(HERE, f)) == h, f
FULL_SHA = "2d31150b27b757a8cc022c34ed83c7271396ab07ef17613a655e17cdda032cbf"; assert sha(FULL) == FULL_SHA
R = json.load(open(FULL))
DOM_KEYS = ("n_req", "tokps", "AL", "ci95_vs_1", "base", "gain_2c", "gain_3c", "gain_cls", "gain_oracle_req_ceiling",
            "capture_cls_of_2c", "capture_cls_of_oracle_req")
pub = {"label": R["label"], "inputs_sha256": dict(R["inputs_sha256"], **{k: v for k, v in SH.items()}, raw_eval_output=FULL_SHA),
       "counts": {"tune_req_domain_fold": R["counts"]["tune_req_domain_fold"], "requests": R["counts"]["requests"]},
       "verdict": R["verdict"], "scen": {}}
for sc, o in R["scen"].items():
    pub["scen"][sc] = {"rho": o["rho"], "verdict": o["verdict"],
                       "dom": {k: {kk: e[kk] for kk in DOM_KEYS} for k, e in o["dom"].items()}}
fit = {"label": "ARTEFATTI STIMATI SU DATI CHE INCLUDONO edit_np (edit): NON PUBBLICARE", "raw_eval_output_sha256": FULL_SHA,
       "counts_extra": {"segments": R["counts"]["segments"], "positions": R["counts"]["positions"]},
       "scen": {sc: {k: o[k] for k in ("folds", "full_tune_selection", "cells_rounds_tune_cf", "cells_rounds_insample")}
                for sc, o in R["scen"].items()}}
s = json.dumps(pub)
for bad in ("table", "theta", "arm1", "arm2c", "arm3c", "cells", "folds", "segments", "positions", "req_id", "prompt"):
    assert bad not in s, bad
json.dump(pub, open(os.path.join(OUT, "hca_results.json"), "x"), indent=1)
json.dump(fit, open(os.path.join(OUT, "edit_np_fitted/hca_fitted_edit_np.json"), "x"), indent=1)
