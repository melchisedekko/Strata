"""Variant (c) of the 'euristica Specu' + honest split (Strata Lead 25/10/2026, 02:49).
tf_d7 (30 real requests, teacher-forced CPU proxy; G9 not applicable), same setup as the P4 rerun (additive cost
s(T)+d*rho_mtp+k*rho_lu, shapes P1/P2/P4, rho_lu of P4). Split stratified by domain with a fixed declared seed.
Selection ONLY on the selection half (objective: max over params of the MIN over domains x band profiles of the point
Δ tok/s vs the baselines), evaluation ONLY on the other half (cluster-bootstrap IC95, B=2000). Both directions.
All tok/s are ESTIMATED (replay), not measurements."""
import json, os, sys, time, itertools
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from strata_sim.sim2 import Profile, load_p4, S_P1, p2_s, walk, boot_ratio, StrataCurrent, GateV2, MtpFixed, Specu, SpecuC
from strata_sim.postprocess import load_tf

SEED = 20261025
TRACE = "/workspace/strata-plus/traces/tf_d7.jsonl"
OUT = "results/v2/split_c"; os.makedirs(OUT, exist_ok=True)
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
BAND = [0.059, 0.0791, 0.0992, 0.1193, 0.1394]          # fascia plausibile (stima di Scout, da misurare su Strata)
CTRL = [0.26]                                           # proxy, solo robustezza
SEL_P = [Profile("%s|rho%.4f" % (sn, r), s, r, RLU, "band") for sn, s in SHAPES.items() for r in BAND]
EVAL_P = SEL_P + [Profile("%s|rho%.4f" % (sn, r), s, r, RLU, "ctrl") for sn, s in SHAPES.items() for r in CTRL]

BASE = {"default": lambda: StrataCurrent(), "spec_cost": lambda: StrataCurrent(spec_cost=True), "k3": lambda: MtpFixed(4)}
GATE_GRID = [dict(tmax=t, skip=sk) for t in (3, 4, 5, 6, 8) for sk in (True, False)]
C_GRID = [dict(min_match=m, factor=f) for m in (3, 4, 5, 6, 8, 10, 12, 16) for f in (None, 0.5, 1.0, 2.0)]
mk_gate = lambda p: GateV2(tmax=p["tmax"], skip=p["skip"], name="gate_v2_t%d%s" % (p["tmax"], "" if p["skip"] else "_noskip"))
mk_c = lambda p: SpecuC(min_match=p["min_match"], factor=p["factor"])


def costs(mk, reqs, prof):
    return walk(mk(), reqs, prof)


def delta(base_rows, rows):   # point Δ tok/s = C_base / C - 1 (same tokens)
    return sum(r["C"] for r in base_rows) / sum(r["C"] for r in rows) - 1


def select(half):
    reqs = HALF[half]
    base = {(b, d, p.name): costs(f, reqs[d], p) for b, f in BASE.items() for d in DOMS for p in SEL_P}
    gs = []
    for gp in GATE_GRID:
        rows = {(d, p.name): costs(lambda: mk_gate(gp), reqs[d], p) for d in DOMS for p in SEL_P}
        ds = [delta(base[(b, d, pn)], rows[(d, pn)]) for b in BASE for (d, pn) in rows]
        gs.append((min(ds), float(np.mean(ds)), gp, rows))
    gs.sort(key=lambda x: (x[0], x[1]), reverse=True)
    g_best, g_rows = gs[0][2], gs[0][3]
    cs = []
    for cp in C_GRID:
        rows = {(d, p.name): costs(lambda: mk_c(cp), reqs[d], p) for d in DOMS for p in SEL_P}
        ds = [delta(base[(b, d, pn)], rows[(d, pn)]) for b in BASE for (d, pn) in rows]
        dg = [delta(g_rows[k], rows[k]) for k in rows]
        cs.append((min(ds + dg), float(np.mean(ds + dg)), cp, min(ds), min(dg)))
    cs.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return dict(gate=g_best, gate_obj=[gs[0][0], gs[0][1]], c=cs[0][2], c_obj=[cs[0][0], cs[0][1]],
                gate_table=[dict(params=x[2], min=x[0], mean=x[1]) for x in gs],
                c_table=[dict(params=x[2], min=x[0], mean=x[1], min_vs_base=x[3], min_vs_gate=x[4]) for x in cs])


def evaluate(half, sel):
    reqs = HALF[half]; out = {}
    pol = dict(BASE); pol["gate*"] = lambda: mk_gate(sel["gate"]); pol["c*"] = lambda: mk_c(sel["c"])
    pol["gate_v2_ref"] = lambda: GateV2(); pol["specu_a"] = lambda: Specu()
    for d in DOMS:
        cl = [q["session"] for q in reqs[d]]
        for p in EVAL_P:
            rows = {n: costs(f, reqs[d], p) for n, f in pol.items()}
            cell = {}
            for cand, refs in (("c*", ("default", "spec_cost", "k3", "gate*")), ("gate*", ("default", "spec_cost", "k3", "c*")),
                               ("gate_v2_ref", ("default", "spec_cost", "k3", "c*")), ("specu_a", ("default", "spec_cost", "k3")),
                               ("c*_vs_ref", ("gate_v2_ref",))):
                cell[cand] = {r: boot_ratio(rows[r], rows[cand.replace("_vs_ref", "")], cl) for r in refs}
            cell["lk_share"] = {n: sum(x["src"]["lk"] for x in rows[n]) / sum(x["R"] for x in rows[n]) for n in ("c*", "gate*", "specu_a")}
            out["%s|%s" % (d, p.name)] = cell
    def verdict(cand, refs, profs):
        bad = [(k, r, cell[cand][r]) for k, cell in out.items() if k.split("|", 1)[1] in profs for r in refs if cell[cand][r][2] < 0]
        return dict(passed=not bad, n_cells=sum(1 for k in out if k.split("|", 1)[1] in profs) * len(refs),
                    clearly_worse=[dict(cell=k, vs=r, ci=v) for k, r, v in bad])
    band = [p.name for p in SEL_P]; allp = [p.name for p in EVAL_P]
    V = {}
    for cand, refs in (("c*", ("default", "spec_cost", "k3", "gate*")), ("gate*", ("default", "spec_cost", "k3", "c*")),
                       ("gate_v2_ref", ("default", "spec_cost", "k3", "c*")), ("specu_a", ("default", "spec_cost", "k3")),
                               ("c*_vs_ref", ("gate_v2_ref",))):
        V[cand] = dict(band=verdict(cand, refs, band), all=verdict(cand, refs, allp))
    return out, V


t0 = time.time(); RES = {"seed": SEED, "split": SPLIT, "trace": TRACE, "profiles_eval": [p.name for p in EVAL_P],
                         "gate_grid": GATE_GRID, "c_grid": C_GRID, "runs": {}}
for s_half, e_half in (("A", "B"), ("B", "A")):
    sel = select(s_half); print("select", s_half, sel["gate"], sel["c"], "%.0fs" % (time.time() - t0), flush=True)
    ev, V = evaluate(e_half, sel); print("eval", e_half, {k: v["all"]["passed"] for k, v in V.items()}, "%.0fs" % (time.time() - t0), flush=True)
    RES["runs"]["sel%s_eval%s" % (s_half, e_half)] = dict(selection=sel, eval=ev, verdict=V)
json.dump(RES, open(os.path.join(OUT, "split.json"), "w"), indent=0, default=float)

# ------------------------------------------------------------------ markdown
f = lambda b: "%+.1f%% [%+.1f, %+.1f]" % (100 * b[0], 100 * b[1], 100 * b[2])
pp = lambda p: ("min_match=%d, lunghezza draft lookup %s" % (p["min_match"], "min(k_lookup,7)" if p["factor"] is None else
                "min(k_lookup,7,⌊%g·match⌋) (max_spec_factor)" % p["factor"])) if "min_match" in p else "tmax=%d, skip=%s" % (p["tmax"], p["skip"])
L = ["# Variante (c) dell'euristica Specu + split onesto — PROXY tf_d7 (30 richieste reali, CPU teacher-forced)", "",
     "tok/s **STIMATI** dal replay (non misure). Costo additivo s(T)+d·ρ_mtp+k·ρ_lu; forme s(T) P1/P2 (stime da codice), P4 "
     "(misurato su CPU, modello denso, non AMD, provvisorio). Fascia plausibile ρ_mtp ∈ {0.059…0.139}: *fascia plausibile, stima di Scout, "
     "da misurare su Strata*; controllo proxy ρ_mtp = 0.26 (solo robustezza). G9 non applicabile (teacher-forced).", "",
     "**Split**: stratificato per dominio, seed = %d (numpy default_rng, permutazione delle richieste ordinate per id, prime 5 → A)." % SEED, ""]
for h in ("A", "B"):
    L.append("- metà %s: " % h + "; ".join("%s: %s" % (d, ", ".join(SPLIT[h][d])) for d in DOMS))
L += ["", "**Selezione** (solo sulla metà di selezione, 15 profili della fascia plausibile × 3 domini): gate_v2 → max del minimo Δ puntuale "
      "vs {default, STRATA_SPEC_COST=1, k=3} su griglia tmax∈{3,4,5,6,8} × skip∈{sì,no}; poi (c) → max del minimo Δ puntuale vs "
      "{default, STRATA_SPEC_COST=1, k=3, gate_v2 scelto} su griglia min_match∈{3,4,5,6,8,10,12,16} × lunghezza lookup ∈ {min(k,7), "
      "⌊f·match⌋ con f∈{0.5,1,2}}. MTP di (c): k∈1..3 con EMA come Specu (non tarato). min_match=3 + min(k,7) ≡ Specu (a) "
      "(il SuffixDrafter non propone match < 3).", "",
      "**Criterio** (Lead): sulla metà di valutazione, in nessuna cella dominio × profilo (15 fascia + 3 controllo 0.26) IC95 interamente < 0 "
      "contro default, STRATA_SPEC_COST=1, k=3 e gate_v2. Con 5 richieste per dominio gli IC sono larghi: il criterio è permissivo.", ""]
for rk, run in RES["runs"].items():
    sel, V, ev = run["selection"], run["verdict"], run["eval"]
    L += ["## %s" % ("Split principale: selezione su A, valutazione su B" if rk == "selA_evalB" else "Split inverso (controllo): selezione su B, valutazione su A"), "",
          "- gate_v2 scelto: %s (obiettivo min %+.1f%%, media %+.1f%% sulla metà di selezione)" % (pp(sel["gate"]), 100 * sel["gate_obj"][0], 100 * sel["gate_obj"][1]),
          "- (c) scelto: %s (obiettivo min %+.1f%%, media %+.1f%%)" % (pp(sel["c"]), 100 * sel["c_obj"][0], 100 * sel["c_obj"][1]),
          "- top-5 (c) in selezione: " + "; ".join("%s → min %+.1f%% (vs baseline %+.1f%%, vs gate %+.1f%%)" % (
              pp(x["params"]), 100 * x["min"], 100 * x["min_vs_base"], 100 * x["min_vs_gate"]) for x in sel["c_table"][:5]),
          "- top-3 gate_v2 in selezione: " + "; ".join("%s → min %+.1f%%" % (pp(x["params"]), 100 * x["min"]) for x in sel["gate_table"][:3]), ""]
    for cand in ("c*", "gate*", "gate_v2_ref", "specu_a", "c*_vs_ref"):
        for scope in ("band", "all"):
            v = V[cand][scope]
            L.append("- **%s** (%s): %s — celle nettamente peggiori %d/%d%s" % (
                cand, "fascia plausibile" if scope == "band" else "fascia + controllo 0.26", "PASSA" if v["passed"] else "NON PASSA",
                len(v["clearly_worse"]), v["n_cells"], (": " + "; ".join("%s vs %s %s" % (x["cell"], x["vs"], f(x["ci"])) for x in v["clearly_worse"])) if v["clearly_worse"] else ""))
    L += ["", "| dominio | profilo | (c)* vs default | (c)* vs SPEC_COST=1 | (c)* vs k=3 | (c)* vs gate_v2* | gate_v2* vs default | gate_v2* vs SPEC_COST=1 | gate_v2* vs k=3 | gate_v2 (tmax 8, non tarato) vs SPEC_COST=1 | gate_v2 (tmax 8) vs (c)* | % round lookup (c)* / gate* |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, c in ev.items():
        d, pn = k.split("|", 1)
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %.0f%% / %.0f%% |" % (d, pn.replace("|", " "), f(c["c*"]["default"]), f(c["c*"]["spec_cost"]), f(c["c*"]["k3"]),
                 f(c["c*"]["gate*"]), f(c["gate*"]["default"]), f(c["gate*"]["spec_cost"]), f(c["gate*"]["k3"]), f(c["gate_v2_ref"]["spec_cost"]), f(c["gate_v2_ref"]["c*"]),
                 100 * c["lk_share"]["c*"], 100 * c["lk_share"]["gate*"]))
    L.append("")
open(os.path.join(OUT, "split.md"), "w").write("\n".join(L) + "\n")
print("done %.0fs" % (time.time() - t0))
