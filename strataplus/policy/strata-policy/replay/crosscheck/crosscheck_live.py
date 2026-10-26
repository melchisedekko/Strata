"""Cross-check: simulated AL / P4-predicted speedup on tf_d7 (teacher-forced) vs Strata Bench LIVE runs (CPU proxy).
Live G9 end-cap rounds (last round, source mtp, k_proposed > configured k) excluded; same rule reproduces Bench's
excluded_endcap_rounds counts. Lookup in sim recomputed with SuffixDrafter max_match=32 (= proxy default, G3).
Speedups: live = Bench's measured CPU wall-clock ratio (runs after 02:07 under concurrent load: less reliable);
sim = predicted with P4 (itself provisional). IC95 bootstrap over requests (B=2000)."""
import json, os, sys, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strata_sim.sim2 import load_p4, walk, MtpFixed, Policy
from strata_sim.postprocess import load_tf

TR = "/workspace/strata-plus/traces"
P4 = load_p4()
R = load_tf(os.path.join(TR, "tf_d7.jsonl"), max_match=32)
DOM = collections.defaultdict(list)
for q in R:
    DOM[q["domain"]].append(q)


class LookupOnly(Policy):
    name = "lookup"
    def act(self, q, i, prof):
        k = int(q["lk_k"][i])
        return ("lk", min(k, 7) + 1, 0, k) if k > 0 else ("none", 1, 0, 0)


class Combo(Policy):
    """Strata-style rule (generate.cpp:16556-16563), as in live_combo_k3: MTP k=3 drafted every round; use the lookup
    draft (<=7) when it agrees with MTP's first token and is longer."""
    name = "combo_k3"
    def act(self, q, i, prof):
        k = int(q["lk_k"][i])
        if k > 3 and int(q["agree"][i]) >= 1:
            return "lk", min(k, 7) + 1, 3, k
        return "mtp", 4, 3, k


def boot(vals_num, vals_den, B=2000, seed=0):
    rng = np.random.default_rng(seed); n = len(vals_num); s = rng.integers(0, n, (B, n))
    num, den = np.array(vals_num, float), np.array(vals_den, float)
    v = num[s].sum(1) / den[s].sum(1)
    return float(num.sum() / den.sum()), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def live(cfg, k):
    tot = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0])); g9 = 0
    for l in open(os.path.join(TR, "live_%s_r0.jsonl" % cfg)):
        o = json.loads(l)
        if o["type"] != "round":
            continue
        tot[o["domain"]][o["req_id"]][0] += o["committed"]; tot[o["domain"]][o["req_id"]][1] += 1
        tot[o["domain"]][o["req_id"]].append(o)
    out = {}
    for d, reqs in tot.items():
        N, Rn = [], []
        for rid, v in reqs.items():
            rs = v[2:]; last = rs[-1]; n_, r_ = v[0], v[1]
            if k and last["source"] == "mtp" and last["k_proposed"] > k:
                n_ -= last["committed"]; r_ -= 1; g9 += 1
            N.append(n_); Rn.append(r_)
        out[d] = boot(N, Rn)
    allN, allR = [], []
    for d, reqs in tot.items():
        for rid, v in reqs.items():
            rs = v[2:]; last = rs[-1]; n_, r_ = v[0], v[1]
            if k and last["source"] == "mtp" and last["k_proposed"] > k:
                n_ -= last["committed"]; r_ -= 1
            allN.append(n_); allR.append(r_)
    out["all"] = boot(allN, allR)
    return out, g9


SUMM = json.load(open(os.path.join(TR, "summary.json")))["configs"]
rows = []
for cfg, pol, k in (("mtp_k1", MtpFixed(2), 1), ("mtp_k2", MtpFixed(3), 2), ("mtp_k3", MtpFixed(4), 3),
                    ("mtp_k5", MtpFixed(6), 5), ("mtp_k7", MtpFixed(8), 7), ("lookup", LookupOnly(), None),
                    ("combo_k3", Combo(), 3)):
    L, g9 = live(cfg, k)
    for d in ("code", "chat", "edit", "all"):
        reqs = R if d == "all" else DOM[d]
        st = walk(pol, reqs, P4)
        al = boot([s["N"] for s in st], [s["R"] for s in st])
        sp = [s["N"] / s["C"] for s in st]                     # per-request predicted speedup (s[0]=1)
        rng = np.random.default_rng(1); idx = rng.integers(0, len(sp), (2000, len(sp))); m = np.array(sp)[idx].mean(1)
        lv = SUMM["live_" + cfg]["by_domain"][d]
        rows.append(dict(cfg=cfg, dom=d, g9=g9, AL_sim=al, AL_live=L[d], dAL=al[0] / L[d][0] - 1,
                         sp_sim=(float(np.mean(sp)), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))),
                         sp_live=(lv["speedup_cpu_robust_mean"], *lv["speedup_cpu_robust_ci95"]), n_live_robust=lv["n_robust"]))
json.dump(rows, open("results/v2/tf_p4/crosscheck_live.json", "w"), indent=1)
t = lambda x: "%.2f [%.2f, %.2f]" % tuple(x)
L = ["# Controllo incrociato simulatore (tf_d7) vs run live Strata Bench (proxy CPU, NON AMD)", "", __doc__, "",
     "| config | dominio | AL sim [IC95] | AL live [IC95] (G9 esclusi) | ΔAL | speedup previsto P4 [IC95] | speedup live CPU robusto [IC95] |",
     "|---|---|---|---|---|---|---|"]
for r in rows:
    L.append("| %s | %s | %s | %s | %+.1f%% | %s | %s |" % (r["cfg"], r["dom"], t(r["AL_sim"]), t(r["AL_live"]), 100 * r["dAL"],
                                                       t(r["sp_sim"]), t(r["sp_live"])))
L.append("\nRound G9 esclusi (solo r0): " + ", ".join("%s %d" % (r["cfg"], r["g9"]) for r in rows if r["dom"] == "all"))
open("results/v2/tf_p4/crosscheck_live.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
