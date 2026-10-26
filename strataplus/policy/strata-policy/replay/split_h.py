"""EXPLORATORY hybrid 'H' (lookup threshold of (c) + MTP depth of gate_v2) tuned ONLY on tf_d7 (30 real requests,
teacher-forced CPU proxy; G9 not applicable). Same protocol as split_c.py: split stratified by domain, seed 20261025,
selection on one half (objective: max over params of the MIN over 3 domains x 15 band profiles of the point Δ tok/s vs
{default, STRATA_SPEC_COST=1, k=3, gate_v2 tmax5 skip, gate_v2 tmax8 skip}), evaluation on the other half (cluster
bootstrap IC95, B=2000), both directions. tok/s are ESTIMATED (replay). Strata v1.1 traces NOT used."""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from strata_sim.sim2 import Profile, load_p4, S_P1, p2_s, walk, boot_ratio, StrataCurrent, GateV2, MtpFixed, HybridH
from strata_sim.postprocess import load_tf

SEED = 20261025
TRACE = "/workspace/strata-plus/traces/tf_d7.jsonl"
OUT = "results/v2/split_h"; os.makedirs(OUT, exist_ok=True)
R = load_tf(TRACE)
DOMS = ["code", "chat", "edit"]
rng = np.random.default_rng(SEED)
HALF = {"A": {}, "B": {}}
for d in DOMS:
    rs = sorted([r for r in R if r["domain"] == d], key=lambda r: str(r["req"]))
    perm = rng.permutation(len(rs)); h = len(rs) // 2
    HALF["A"][d] = [rs[j] for j in sorted(perm[:h])]; HALF["B"][d] = [rs[j] for j in sorted(perm[h:])]
SPLIT = {k: {d: [str(r["req"]) for r in v[d]] for d in DOMS} for k, v in HALF.items()}
P4 = load_p4(); RLU = P4.rho_lu
SHAPES = {"P1": S_P1, "P2": p2_s(), "P4": P4.s}
BAND = [0.059, 0.0791, 0.0992, 0.1193, 0.1394]
SEL_P = [Profile("%s|rho%.4f" % (sn, r), s, r, RLU, "band") for sn, s in SHAPES.items() for r in BAND]
EVAL_P = SEL_P + [Profile("%s|rho%.4f" % (sn, 0.26), s, 0.26, RLU, "ctrl") for sn, s in SHAPES.items()]
REFS = {"default": lambda: StrataCurrent(), "spec_cost": lambda: StrataCurrent(spec_cost=True), "k3": lambda: MtpFixed(4),
        "gate_t5": lambda: GateV2(tmax=5, skip=True, name="gate_v2_t5"), "gate_t8": lambda: GateV2(tmax=8, skip=True)}
H_GRID = [dict(min_match=m, factor=f, tmax=t) for m in (3, 4, 6, 8, 12, 16) for f in (None, 1.0) for t in (5, 8)]
mk_h = lambda p: HybridH(min_match=p["min_match"], factor=p["factor"], tmax=p["tmax"])
delta = lambda b, r: sum(x["C"] for x in b) / sum(x["C"] for x in r) - 1


def select(half):
    reqs = HALF[half]
    base = {(b, d, p.name): walk(f(), reqs[d], p) for b, f in REFS.items() for d in DOMS for p in SEL_P}
    hs = []
    for hp in H_GRID:
        rows = {(d, p.name): walk(mk_h(hp), reqs[d], p) for d in DOMS for p in SEL_P}
        ds = {b: [delta(base[(b, d, pn)], rows[(d, pn)]) for (d, pn) in rows] for b in REFS}
        allv = sum(ds.values(), [])
        hs.append(dict(params=hp, min=min(allv), mean=float(np.mean(allv)), min_by_ref={b: min(v) for b, v in ds.items()}))
    hs.sort(key=lambda x: (x["min"], x["mean"]), reverse=True)
    return dict(h=hs[0]["params"], h_obj=[hs[0]["min"], hs[0]["mean"]], table=hs)


def evaluate(half, hp):
    reqs = HALF[half]; out = {}
    pol = dict(REFS); pol["H*"] = lambda: mk_h(hp)
    for d in DOMS:
        cl = [q["session"] for q in reqs[d]]
        for p in EVAL_P:
            rows = {n: walk(f(), reqs[d], p) for n, f in pol.items()}
            cell = {"H*": {r: boot_ratio(rows[r], rows["H*"], cl) for r in REFS},
                    "gate_t8": {"gate_t5": boot_ratio(rows["gate_t5"], rows["gate_t8"], cl)},
                    "lk_share_H": sum(x["src"]["lk"] for x in rows["H*"]) / sum(x["R"] for x in rows["H*"])}
            out["%s|%s" % (d, p.name)] = cell
    band = {p.name for p in SEL_P}
    def verdict(refs, scope):
        bad = [dict(cell=k, vs=r, ci=c["H*"][r]) for k, c in out.items() if (scope == "all" or k.split("|", 1)[1] in band)
               for r in refs if c["H*"][r][2] < 0]
        n = sum(1 for k in out if scope == "all" or k.split("|", 1)[1] in band) * len(refs)
        return dict(passed=not bad, n_cells=n, clearly_worse=bad)
    V = {s: {"vs_baselines": verdict(("default", "spec_cost", "k3"), s), "vs_gate": verdict(("gate_t5", "gate_t8"), s),
             "vs_all": verdict(tuple(REFS), s)} for s in ("band", "all")}
    return out, V


t0 = time.time(); RES = {"seed": SEED, "split": SPLIT, "trace": TRACE, "grid": H_GRID, "refs": list(REFS), "runs": {}}
for sh, eh in (("A", "B"), ("B", "A")):
    sel = select(sh); print("select", sh, sel["h"], ["%.4f" % x for x in sel["h_obj"]], "%.0fs" % (time.time() - t0), flush=True)
    ev, V = evaluate(eh, sel["h"])
    print("eval", eh, {s: {k: (v["passed"], len(v["clearly_worse"]), v["n_cells"]) for k, v in V[s].items()} for s in V}, flush=True)
    RES["runs"]["sel%s_eval%s" % (sh, eh)] = dict(selection=sel, eval=ev, verdict=V)
json.dump(RES, open(os.path.join(OUT, "split_h.json"), "w"), indent=0, default=float)

f = lambda b: "%+.1f%% [%+.1f, %+.1f]" % (100 * b[0], 100 * b[1], 100 * b[2])
pp = lambda p: "min_match=%d, lookup %s, gate_v2 tmax=%d" % (p["min_match"], "min(k,7)" if p["factor"] is None else "min(k,7,⌊%g·match⌋)" % p["factor"], p["tmax"])
L = ["# Ibrido H (ESPLORATIVO, non candidabile per questa patch) — PROXY tf_d7, tok/s STIMATI", "",
     "Lookup se match ≥ min_match (lunghezza min(k,7) o ⌊f·match⌋), altrimenti none/MTP e profondità decise da gate_v2 (JointGate, senza sorgente lookup). "
     "Split stratificato seed %d (identico a split_c). Griglia: min_match∈{3,4,6,8,12,16} × {min(k,7), f=1} × tmax∈{5,8} (24). "
     "Obiettivo: max del minimo Δ puntuale vs {default, SPEC_COST=1, k=3, gate_v2 t5, gate_v2 t8} su 15 profili fascia plausibile "
     "(*stima di Scout, da misurare su Strata*) × 3 domini. Valutazione: IC95 bootstrap a cluster; 0.26 solo controllo." % SEED, ""]
for rk, run in RES["runs"].items():
    sel, V, ev = run["selection"], run["verdict"], run["eval"]
    L += ["## " + ("Selezione A → valutazione B" if rk == "selA_evalB" else "Split inverso: selezione B → valutazione A"), "",
          "- H scelto: %s (min %+.1f%%, media %+.1f%%)" % (pp(sel["h"]), 100 * sel["h_obj"][0], 100 * sel["h_obj"][1]),
          "- top-5: " + "; ".join("%s → min %+.1f%% / media %+.1f%%" % (pp(x["params"]), 100 * x["min"], 100 * x["mean"]) for x in sel["table"][:5])]
    for s in ("band", "all"):
        for k, v in V[s].items():
            L.append("- %s, %s: %s — %d/%d celle nettamente peggiori%s" % ("fascia" if s == "band" else "fascia+0.26", k, "PASSA" if v["passed"] else "NON PASSA",
                     len(v["clearly_worse"]), v["n_cells"], (": " + "; ".join("%s vs %s %s" % (x["cell"], x["vs"], f(x["ci"])) for x in v["clearly_worse"])) if v["clearly_worse"] else ""))
    L += ["", "| dominio | profilo | H* vs default | H* vs SPEC_COST=1 | H* vs k=3 | H* vs gate t5 | H* vs gate t8 | gate t8 vs t5 | % round lookup H* |", "|---|---|---|---|---|---|---|---|---|"]
    for k, c in ev.items():
        d, pn = k.split("|", 1)
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %.0f%% |" % (d, pn.replace("|", " "), *[f(c["H*"][r]) for r in REFS], f(c["gate_t8"]["gate_t5"]), 100 * c["lk_share_H"]))
    L.append("")
open(os.path.join(OUT, "split_h.md"), "w").write("\n".join(L) + "\n")
print("done %.0fs" % (time.time() - t0))
