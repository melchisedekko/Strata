"""Variant family (Hedge full-feedback / contextual / agreement / deterministic / current+full-feedback) scored in the
v2 walk against the v2 baselines and the main candidate gate_v2. Same data, profiles (P1,P2,B-flat,B-lin; P4 if
present), cluster bootstrap. Output: <out>/variants.json and variants.md. Labels as in run_v2."""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from strata_sim.sim2 import base_profiles, walk, summarize, boot_ratio, StrataCurrent, GateV2, MtpFixed
from strata_sim.synth2 import make_domain
from strata_sim.postprocess import load_tf
from strata_sim.v1adapt import variants

ap = argparse.ArgumentParser(); ap.add_argument("--data", default="synthetic"); ap.add_argument("--n", type=int, default=48)
ap.add_argument("--out", default=None); A = ap.parse_args()
if A.data == "synthetic":
    LABEL = "SYNTHETIC - NOT a measurement"
    DATA = {d: make_domain(d, A.n if d != "edit" else A.n // 2, seed=7 + k, session_len=8)
            for k, d in enumerate(["code", "chat", "edit", "session"])}
    out = A.out or "results/v2/synthetic"
else:
    R = load_tf(A.data.split(":", 1)[1]); LABEL = "TEACHER-FORCED proxy trace - costs symbolic - NOT a live measurement"
    DATA = {}
    for r in R:
        DATA.setdefault(r["domain"], []).append(r)
    out = A.out or "results/v2/tf"
os.makedirs(out, exist_ok=True)
t0 = time.time(); res = {}
lines = ["# Varianti (famiglia v1 nel walk v2) — %s" % A.data, "", "**Dati:** " + LABEL + ". tok/s stimati con profili simbolici "
         "(P1/P2 stime da codice, B-flat/B-lin limiti). Δ = rapporto tok/s con IC95 bootstrap a cluster.", "",
         "| dominio | profilo | policy | speedup | AL | Δ vs strata_current | Δ vs strata_cost | Δ vs gate_v2 |", "|---|---|---|---|---|---|---|---|"]
f = lambda b: "%+.1f%% [%+.1f, %+.1f]" % (100 * b[0], 100 * b[1], 100 * b[2])
for dom, reqs in DATA.items():
    cl = [q["session"] for q in reqs]
    for prof in base_profiles(rho_lu=0.001):
        base = {p.name: walk(p, reqs, prof) for p in (StrataCurrent(), StrataCurrent(spec_cost=True), GateV2())}
        for p in [None] + variants():
            items = base.items() if p is None else [(p.name, walk(p, reqs, prof))]
            for nm, rows in items:
                s = summarize(rows, prof)
                b = {k: boot_ratio(base[r], rows, cl) for k, r in (("cur", "strata_current"), ("cost", "strata_cost"), ("gate", "gate_v2"))}
                res["%s|%s|%s" % (dom, prof.name, nm)] = dict(tps=s["tps"], speedup=s["speedup"], AL=s["AL"], **{"vs_" + k: v for k, v in b.items()})
                lines.append("| %s | %s | %s | %.3f | %.2f | %s | %s | %s |" % (dom, prof.name, nm, s["speedup"], s["AL"], f(b["cur"]), f(b["cost"]), f(b["gate"])))
    print(dom, "%.0fs" % (time.time() - t0), flush=True)
json.dump({"label": LABEL, "cells": res}, open(os.path.join(out, "variants.json"), "w"), indent=0, default=float)
open(os.path.join(out, "variants.md"), "w").write("\n".join(lines) + "\n")
print("done", out)
