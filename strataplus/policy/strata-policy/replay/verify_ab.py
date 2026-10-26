"""Tune-set check of gate_v2 arms A (tmax 5, skip) and B (tmax 8, skip) vs default, STRATA_SPEC_COST=1, k=3 on tf_d7
(30 real requests, CPU teacher-forced proxy; G9 n/a): scopes full (30), half B, half A (split seed 20261025);
band ρ_mtp 0.059..0.1394 × P1/P2/P4 (decides) + control 0.26. Cell class: worse (IC95 < 0), better (IC95 > 0), neutral.
Also B vs A, and the window-size histogram of the rounds played. tok/s ESTIMATED.  usage: verify_ab.py OUT.json [P4_COST.json]"""
import json, os, sys, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from strata_sim.sim2 import Profile, load_p4, S_P1, p2_s, walk, boot_ratio, StrataCurrent, GateV2, MtpFixed
from strata_sim.postprocess import load_tf

R = load_tf("/workspace/strata-plus/traces/tf_d7.jsonl"); DOMS = ["code", "chat", "edit"]
rng = np.random.default_rng(20261025); HALF = {"A": {}, "B": {}}
for d in DOMS:
    rs = sorted([r for r in R if r["domain"] == d], key=lambda r: str(r["req"]))
    perm = rng.permutation(len(rs)); h = len(rs) // 2
    HALF["A"][d] = [rs[j] for j in sorted(perm[:h])]; HALF["B"][d] = [rs[j] for j in sorted(perm[h:])]
SC = {"full": {d: [r for r in R if r["domain"] == d] for d in DOMS}, "halfB": HALF["B"], "halfA": HALF["A"]}
P4 = load_p4(sys.argv[2]) if len(sys.argv) > 2 else load_p4(); SH = {"P1": S_P1, "P2": p2_s(), "P4": P4.s}
PROFS = [Profile("%s|rho%.4f" % (sn, r), s, r, P4.rho_lu, "band" if r < 0.2 else "ctrl")
         for sn, s in SH.items() for r in (0.059, 0.0791, 0.0992, 0.1193, 0.1394, 0.26)]
POL = {"default": lambda: StrataCurrent(), "spec_cost": lambda: StrataCurrent(spec_cost=True), "k3": lambda: MtpFixed(4),
       "A": lambda: GateV2(tmax=5, skip=True), "B": lambda: GateV2(tmax=8, skip=True)}
cls = lambda ci: "worse" if ci[2] < 0 else "better" if ci[1] > 0 else "neutral"
OUT = {"cells": {}, "T_hist": {}}
for sc, reqs in SC.items():
    for d in DOMS:
        cl = [q["session"] for q in reqs[d]]
        for p in PROFS:
            rows = {n: walk(f(), reqs[d], p) for n, f in POL.items()}
            c = {}
            for arm in ("A", "B"):
                for ref in ("default", "spec_cost", "k3"):
                    ci = boot_ratio(rows[ref], rows[arm], cl); c["%s_vs_%s" % (arm, ref)] = dict(ci=ci, cls=cls(ci))
            ci = boot_ratio(rows["A"], rows["B"], cl); c["B_vs_A"] = dict(ci=ci, cls=cls(ci))
            OUT["cells"]["%s|%s|%s" % (sc, d, p.name)] = c
# window-size histogram of arm B (and A) on all 30 requests, band profiles
for arm in ("A", "B"):
    H = collections.Counter(); n = 0
    pol_T = []
    for p in PROFS:
        if p.label != "band": continue
        for d in DOMS:
            pol = POL[arm](); orig = pol.act
            def act(q, i, pr, orig=orig):
                r = orig(q, i, pr); T = max(1, min(r[1], q["n"] - i)) if r[0] != "none" else 1; H[(r[0], T)] += 1; return r
            pol.act = act; walk(pol, SC["full"][d], p)
    tot = sum(H.values())
    OUT["T_hist"][arm] = {"%s_T%d" % k: v for k, v in sorted(H.items())}
    OUT["T_hist"][arm + "_maxT"] = max(T for _, T in H)
    OUT["T_hist"][arm + "_share_T8"] = sum(v for (s, T), v in H.items() if T == 8) / tot
    OUT["T_hist"][arm + "_share_T_ge9"] = sum(v for (s, T), v in H.items() if T >= 9) / tot
OUT["p4"] = dict(path=sys.argv[2] if len(sys.argv) > 2 else "default", s=P4.s, rho_mtp=P4.rho_mtp, rho_lu=P4.rho_lu)
json.dump(OUT, open(sys.argv[1], "w"), indent=0, default=float)
summ = collections.Counter((k.split("|")[0], "band" if "0.2600" not in k else "ctrl", n, v["cls"]) for k, c in OUT["cells"].items() for n, v in c.items())
for sc in SC:
    for arm in ("A", "B"):
        w = sum(summ[(sc, "band", "%s_vs_%s" % (arm, r), "worse")] for r in ("default", "spec_cost", "k3"))
        wc = sum(summ[(sc, "ctrl", "%s_vs_%s" % (arm, r), "worse")] for r in ("default", "spec_cost", "k3"))
        print(sc, arm, "worse band", w, "ctrl", wc)
    print(sc, "B_vs_A band better/neutral/worse", [summ[(sc, "band", "B_vs_A", x)] for x in ("better", "neutral", "worse")])
print({k: v for k, v in OUT["T_hist"].items() if "share" in k or "max" in k})
