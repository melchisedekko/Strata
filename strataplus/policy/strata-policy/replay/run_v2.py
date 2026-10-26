"""E2-E4 replay (piano v2): policies x profiles x domains, oracles, bootstrap, go/no-go table, sensitivity map.
Data: --data synthetic (synth2, SYNTHETIC) or --data tf:<path> (strataplus.v1 teacher-forced trace, e.g. Strata
Bench proxy CPU). Labels are written into every output."""
import argparse, json, os, sys, time
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from strata_sim import sim2
from strata_sim.sim2 import (Profile, StrataCurrentCF, GateV2Native, base_profiles, s_alpha, walk, summarize, boot_ratio, oracle_dp, oracle_round,
                             NoSpec, MtpFixed, StrataCurrent, GateV2, MtpAdaEDL, Specu)
from strata_sim.synth2 import make_domain
from strata_sim.postprocess import load_tf

ap = argparse.ArgumentParser()
ap.add_argument("--data", default="synthetic")
ap.add_argument("--out", default=None)
ap.add_argument("--n", type=int, default=48)
ap.add_argument("--grid", action="store_true")
ap.add_argument("--procs", type=int, default=6)
A = ap.parse_args()

if A.data == "synthetic":
    LABEL = "SYNTHETIC (synth2: toy token streams + toy MTP; lookup/pool = production SuffixDrafter) - NOT a measurement"
    DATA = {d: make_domain(d, A.n if d != "edit" else A.n // 2, seed=7 + k, session_len=8)
            for k, d in enumerate(["code", "chat", "edit", "session"])}
    out = A.out or "results/v2/synthetic"
else:
    path = A.data.split(":", 1)[1]
    R = load_tf(path)
    LABEL = "TEACHER-FORCED %s trace %s: MTP candidates REAL (%s); lookup/pool recomputed; costs = symbolic profiles" % (
        R[0]["label"] if R else "", os.path.basename(path), R[0]["label"] if R else "")
    DATA = {}
    for r in R:
        DATA.setdefault(r["domain"], []).append(r)
    out = A.out or "results/v2/tf"
os.makedirs(out, exist_ok=True)


def policies():
    return [NoSpec(), MtpFixed(4), StrataCurrent(), StrataCurrent(spec_cost=True), StrataCurrent(lookup=False, spec_cost=True),
            StrataCurrent(src="pl"), GateV2(), GateV2(conf_stop=True), GateV2(skip=False), GateV2(srcs=()), MtpAdaEDL(),
            GateV2(srcs=("lk", "pl")), GateV2(srcs=("pl",)), StrataCurrentCF(spec_cost=True), GateV2Native(), Specu()]


def run_cell(args):
    dom, prof, which = args
    reqs = DATA[dom]
    res = {}
    for p in policies():
        if which and p.name not in which:
            continue
        rows = walk(p, reqs, prof)
        res[p.name] = rows
    orc = {}
    if not which:
        for nm, srcs in (("O_DP", ("mtp", "lk", "pl")), ("O_DP_nopool", ("mtp", "lk")), ("O_depth", ("mtp",)),
                         ("O_round", ("mtp", "lk", "pl")), ("O_round_nopool", ("mtp", "lk"))):
            f = oracle_dp if nm.startswith("O_DP") or nm == "O_depth" else oracle_round
            orc[nm] = [f(q, prof, srcs) for q in reqs]
    return dom, prof.name, res, orc


def main():
    t0 = time.time()
    profs = base_profiles(rho_lu=0.001)
    cells = [(d, p, None) for d in DATA for p in profs]
    with Pool(A.procs) as pool:
        results = pool.map(run_cell, cells)
    summ = {"label": LABEL, "n_requests": {d: len(v) for d, v in DATA.items()},
            "n_tokens": {d: int(sum(q["n"] for q in v)) for d, v in DATA.items()},
            "profiles": {p.name: dict(s=p.s, rho_mtp=p.rho_mtp, rho_lu=p.rho_lu, label=p.label) for p in profs}, "cells": {}}
    for dom, pn, res, orc in results:
        prof = next(p for p in profs if p.name == pn)
        reqs = DATA[dom]
        cl = [q["session"] for q in reqs]
        N = sum(q["n"] for q in reqs)
        cell = {"policies": {}, "oracles": {}}
        for nm, C in orc.items():
            cell["oracles"][nm] = dict(tps=N / sum(C), speedup=N * prof.s[0] / sum(C))
        base = res["strata_current"]
        for nm, rows in res.items():
            s = summarize(rows, prof)
            s["G_vs_O_DP"] = 1 - s["tps"] / cell["oracles"]["O_DP"]["tps"]
            s["G_vs_O_round"] = 1 - s["tps"] / cell["oracles"]["O_round"]["tps"]
            s["G_vs_O_DP_nopool"] = 1 - s["tps"] / cell["oracles"]["O_DP_nopool"]["tps"]
            s["G_vs_O_depth"] = 1 - s["tps"] / cell["oracles"]["O_depth"]["tps"]
            s["vs_strata_current"] = boot_ratio(base, rows, cl)
            s["vs_strata_cost"] = boot_ratio(res["strata_cost"], rows, cl)
            s["vs_mtp_fixed_k3"] = boot_ratio(res["mtp_fixed_k3"], rows, cl)
            s["vs_gate_v2"] = boot_ratio(res["gate_v2"], rows, cl)
            s["vs_strata_cost_mtponly"] = boot_ratio(res["strata_cost_mtponly"], rows, cl)
            if "specu" in res:
                s["vs_specu"] = boot_ratio(res["specu"], rows, cl)
            cell["policies"][nm] = s
        summ["cells"]["%s|%s" % (dom, pn)] = cell
    json.dump(summ, open(os.path.join(out, "summary.json"), "w"), indent=1, default=float)
    print("main done %.0fs" % (time.time() - t0), flush=True)

    if A.grid:
        grid = []
        for al in (0.0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0):
            for rm in (0.0, 0.03, 0.059, 0.1, 0.2, 0.3):
                for rl in (0.0, 0.001, 0.01):
                    grid.append(Profile("g_a%.2f_m%.3f_l%.3f" % (al, rm, rl), s_alpha(al), rm, rl, "sensitivity grid"))
        which = {"strata_current", "strata_cost", "gate_v2", "gate_v2_pool", "mtp_fixed_k3", "strata_cost_mtponly",
                 "gate_v2_nolookup", "mtp_adaedl", "gate_v2_conf", "specu"}
        cells = [(d, p, which) for d in DATA for p in grid]
        sim2_grid = {p.name: p for p in grid}
        with Pool(A.procs) as pool:
            results = pool.map(run_cell, cells)
        G = {}
        for dom, pn, res, _ in results:
            cl = [q["session"] for q in DATA[dom]]
            G["%s|%s" % (dom, pn)] = {nm: boot_ratio(res["strata_current"], rows, cl) for nm, rows in res.items()} | \
                {"cost:" + nm: boot_ratio(res["strata_cost"], rows, cl) for nm, rows in res.items()} | \
                {"k3:" + nm: boot_ratio(res["mtp_fixed_k3"], rows, cl) for nm, rows in res.items()} | \
                {"costmo:" + nm: boot_ratio(res["strata_cost_mtponly"], rows, cl) for nm, rows in res.items()}
        json.dump({"label": LABEL, "grid": G}, open(os.path.join(out, "grid.json"), "w"), indent=0, default=float)
        print("grid done %.0fs" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
