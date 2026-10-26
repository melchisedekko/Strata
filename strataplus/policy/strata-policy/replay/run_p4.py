"""Rerun with the MEASURED P4 cost profile (Strata Bench, dense 2B on CPU, NOT AMD, provisional) + dense rho_mtp grid.
Go/no-go of piano §8 (H1, H4a, H4b) + Strata Lead's 'euristica Specu' check, per domain, cluster-bootstrap IC95 on
every number. Costs additive: s(T) + d*rho_mtp + k*rho_lu.  Output: <out>/p4.json, <out>/p4.md.
Data: tf:<trace> (teacher-forced proxy, 30 real requests) or synthetic (synth2, NOT a measurement)."""
import argparse, json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from strata_sim.sim2 import (Profile, load_p4, S_P1, p2_s, walk, boot_ratio, oracle_dp, oracle_round,
                             StrataCurrent, GateV2, MtpFixed, Specu, SpecuCost)
from strata_sim.synth2 import make_domain
from strata_sim.postprocess import load_tf

ap = argparse.ArgumentParser(); ap.add_argument("--data", default="tf:/workspace/strata-plus/traces/tf_d7.jsonl")
ap.add_argument("--out", default=None); ap.add_argument("--n", type=int, default=48); A = ap.parse_args()
if A.data == "synthetic":
    LABEL = "SINTETICO (synth2) - NON è una misura"
    DATA = {d: make_domain(d, A.n if d != "edit" else A.n // 2, seed=7 + k, session_len=8)
            for k, d in enumerate(["code", "chat", "edit"])}
    out = A.out or "results/v2/synthetic_p4"
else:
    R = load_tf(A.data.split(":", 1)[1])
    LABEL = ("PROXY teacher-forced %s (30 richieste reali, Qwen3.5-2B denso su CPU): candidati MTP reali, lookup "
             "ricalcolato con SuffixDrafter (max_match 64); tok/s STIMATI con i profili di costo" % os.path.basename(A.data))
    DATA = {}
    for r in R:
        DATA.setdefault(r["domain"], []).append(r)
    out = A.out or "results/v2/tf_p4"
os.makedirs(out, exist_ok=True)

P4, P4lo, P4hi = load_p4(), load_p4(variant="lo"), load_p4(variant="hi")
RLU = P4.rho_lu
SHAPES = {"P1": S_P1, "P2": p2_s(), "P4": P4.s}
MAIN = [Profile("P1", S_P1, 0.059, 0.001, "stima da codice (verify.hpp), rho_mtp 0.059"),
        Profile("P2", p2_s(), 0.059, 0.001, "stima da codice, rho_mtp 0.059"),
        P4, P4lo, P4hi,
        Profile("P1@rhoP4", S_P1, P4.rho_mtp, RLU, "s(T) di P1, rho_mtp misurato P4"),
        Profile("P2@rhoP4", p2_s(), P4.rho_mtp, RLU, "s(T) di P2, rho_mtp misurato P4")]
RHOS = [round(x, 4) for x in np.linspace(0.059, 0.26, 11)]
GRID = [Profile("%s|rho%.4f" % (sn, r), s, r, RLU, "griglia") for sn, s in SHAPES.items() for r in RHOS]


def pols():
    return ([StrataCurrent(), StrataCurrent(spec_cost=True), StrataCurrent(lookup=False, spec_cost=True), Specu(), SpecuCost(),
             GateV2(), GateV2(conf_stop=True)] + [MtpFixed(k + 1) for k in range(1, 8)])


def boot_al(rows, cl, B=2000, seed=0, num=lambda r: r["N"], den=lambda r: r["R"]):
    """cluster-bootstrap IC95 of sum(num)/sum(den) (AL by default)."""
    rng = np.random.default_rng(seed); keys = sorted(set(cl)); g = [[j for j, c in enumerate(cl) if c == k] for k in keys]
    N = np.array([sum(num(rows[j]) for j in x) for x in g], float); Rr = np.array([sum(den(rows[j]) for j in x) for x in g], float)
    s = rng.integers(0, len(g), (B, len(g))); v = N[s].sum(1) / Rr[s].sum(1)
    return float(N.sum() / Rr.sum()), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def cell(dom, prof, oracles=True):
    reqs = DATA[dom]; cl = [q["session"] for q in reqs]; N = sum(q["n"] for q in reqs)
    res = {p.name: walk(p, reqs, prof) for p in pols()}
    if oracles:
        for nm, f, srcs in (("O_round", oracle_round, ("mtp", "lk")), ("O_DP", oracle_dp, ("mtp", "lk")),
                            ("O_depth", oracle_dp, ("mtp",))):
            res[nm] = [dict(N=q["n"], C=f(q, prof, srcs), R=1) for q in reqs]
    o = {"N": N, "pol": {}}
    for nm, rows in res.items():
        C = sum(r["C"] for r in rows)
        d = dict(speedup=N * prof.s[0] / C, speedup_ci=boot_al(rows, cl, den=lambda r: r["C"] / prof.s[0]))
        if not nm.startswith("O_"):
            d["AL"] = boot_al(rows, cl)
            Rn = sum(r["R"] for r in rows); d["d_mtp_per_round"] = sum(r["dm"] for r in rows) / Rn
            d["frac_lookup"] = sum(r["src"]["lk"] for r in rows) / Rn
            d["d_ci"] = boot_al(rows, cl, num=lambda r: r["dm"]); d["lk_ci"] = boot_al(rows, cl, num=lambda r: r["src"]["lk"])
            d["vs_current"] = boot_ratio(res["strata_current"], rows, cl)
            d["vs_cost"] = boot_ratio(res["strata_cost"], rows, cl)
            d["vs_k3"] = boot_ratio(res["mtp_fixed_k3"], rows, cl)
            d["vs_specu"] = boot_ratio(res["specu"], rows, cl)
            d["vs_specu_costdepth"] = boot_ratio(res["specu_costdepth"], rows, cl)
            if oracles:   # G = 1 - tps/tps_oracle, IC95 via the same paired bootstrap
                for on in ("O_round", "O_DP", "O_depth"):
                    b = boot_ratio(res[on], rows, cl); d["G_" + on] = (-b[0], -b[2], -b[1])
        o["pol"][nm] = d
    ks = ["mtp_fixed_k%d" % k for k in range(1, 8)]
    o["best_fixed_k"] = int(max(ks, key=lambda k: o["pol"][k]["speedup"])[-1])
    return o


t0 = time.time()
M = {"%s|%s" % (d, p.name): cell(d, p) for d in DATA for p in MAIN}
print("main %.0fs" % (time.time() - t0), flush=True)
G = {"%s|%s" % (d, p.name): cell(d, p, oracles=False) for d in DATA for p in GRID}
print("grid %.0fs" % (time.time() - t0), flush=True)
prof_info = {p.name: dict(s=p.s, rho_mtp=p.rho_mtp, rho_lu=p.rho_lu, label=p.label) for p in MAIN}
json.dump({"label": LABEL, "profiles": prof_info, "rhos": RHOS, "main": M, "grid": G},
          open(os.path.join(out, "p4.json"), "w"), indent=0, default=float)

# ------------------------------------------------------------------ markdown
f = lambda b: "%+.1f%% [%+.1f, %+.1f]" % (100 * b[0], 100 * b[1], 100 * b[2])
g = lambda b: "%.1f%% [%.1f, %.1f]" % (100 * b[0], 100 * b[1], 100 * b[2])
al = lambda b: "%.2f [%.2f, %.2f]" % b
doms = list(DATA)
L = ["# Rerun con P4 — %s" % A.data, "", "**Dati:** " + LABEL + ".", "",
     "**P4:** " + P4.label + ". s(T) = " + ", ".join("%.3f" % x for x in P4.s) + "; rho_mtp = %.4f [%.4f, %.4f]; rho_lu = %.1e. "
     % (P4.rho_mtp, P4lo.rho_mtp, P4hi.rho_mtp, P4.rho_lu) + "P4-lo/P4-hi = estremi IC95 di s(T) e rho_mtp insieme. "
     "Costo additivo s(T) + d·rho_mtp + k·rho_lu. Tutti i Δ sono rapporti di tok/s STIMATI con IC95 bootstrap a cluster (richiesta).", "",
     "> `gate_v2_conf` (stop su confidenza) è **non valutabile**: `cand.mtp.probs` sono probabilità del sampler (G2/D11).", ""]
for pn in [p.name for p in MAIN]:
    L += ["## Profilo %s — %s" % (pn, prof_info[pn]["label"]), "",
          "| dominio | policy | speedup | AL [IC95] | d MTP/round | %% lookup | Δ vs default | Δ vs STRATA_SPEC_COST=1 | Δ vs k3 | Δ vs Specu | G O_round | G O_depth |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in doms:
        c = M["%s|%s" % (d, pn)]
        for nm in ("strata_current", "strata_cost", "strata_cost_mtponly", "mtp_fixed_k3", "specu", "specu_costdepth", "gate_v2"):
            x = c["pol"][nm]
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                d, nm, "%.3f [%.3f, %.3f]" % tuple(x["speedup_ci"]), al(x["AL"]), al(x["d_ci"]), g(x["lk_ci"]), f(x["vs_current"]), f(x["vs_cost"]),
                f(x["vs_k3"]), f(x["vs_specu"]), g(x["G_O_round"]), g(x["G_O_depth"])))
        sc = lambda n: "%.3f [%.3f, %.3f]" % tuple(c["pol"][n]["speedup_ci"])
        L.append("| %s | *oracoli / k fisso* | O_round %s, O_DP %s, O_depth %s; k fisso migliore = %d (speedup %s) | | | | | | | | | |" % (
            d, sc("O_round"), sc("O_DP"), sc("O_depth"), c["best_fixed_k"], sc("mtp_fixed_k%d" % c["best_fixed_k"])))
    L.append("")

# go/no-go
def verdict(key, profs, cand="gate_v2", src=M):
    rows, ok = [], True
    for pn in profs:
        bs = [src["%s|%s" % (d, pn)]["pol"][cand][key] for d in doms]
        pos = sum(b[1] > 0 for b in bs); neg = sum(b[2] < 0 for b in bs)
        good = pos >= 2 and neg == 0
        ok &= good
        rows.append((pn, good, pos, neg, bs))
    return ok, rows

L += ["## Go/no-go (piano §8) — %s" % ("PROXY tf_d7" if A.data != "synthetic" else "SINTETICO"), ""]
for title, key in (("H1 go: gate_v2 vs DraftPolicy default", "vs_current"), ("H4(a) go: gate_v2 vs STRATA_SPEC_COST=1", "vs_cost"),
                   ("H4(b) go: gate_v2 vs MTP fisso k=3", "vs_k3"), ("Lead: gate_v2 vs euristica Specu", "vs_specu"),
                   ("(info) gate_v2 vs Specu con profondità STRATA_SPEC_COST", "vs_specu_costdepth")):
    ok, rows = verdict(key, ["P1", "P2", "P4", "P4-lo", "P4-hi"])
    okg, rg = verdict(key, [p.name for p in GRID], src=G)
    L.append("**%s** — P1/P2/P4(±IC): %s; griglia rho_mtp∈[0.059,0.26]×{P1,P2,P4}: %s (%d/%d profili OK)" % (
        title, "GO" if ok else "NO-GO", "GO" if okg else "NO-GO", sum(r[1] for r in rg), len(rg)))
    for pn, good, pos, neg, bs in rows:
        L.append("- %s: %s — %s" % (pn, "ok" if good else "no", "; ".join("%s %s" % (d, f(b)) for d, b in zip(doms, bs))))
    band = [r for r in rg if float(r[0].split("rho")[1]) <= 0.15]
    L.append("- fascia plausibile rho_mtp∈[0.06,0.15] (stima di Scout, da misurare su Strata): %d/%d profili OK, %d con un dominio IC95 interamente < 0" % (
        sum(r[1] for r in band), len(band), sum(r[3] > 0 for r in band)))
    bad = [r[0] for r in rg if not r[1]]
    if bad:
        L.append("- griglia, profili che falliscono: " + ", ".join(bad))
    L.append("")
L.append("### Stessi criteri applicati alle euristiche Specu (come candidato patch)\n")
for cand in ("specu", "specu_costdepth"):
    for title, key in (("vs default", "vs_current"), ("vs STRATA_SPEC_COST=1", "vs_cost"), ("vs k=3", "vs_k3")):
        ok, rows = verdict(key, ["P1", "P2", "P4", "P4-lo", "P4-hi"], cand=cand)
        okg, rg = verdict(key, [p.name for p in GRID], cand=cand, src=G)
        band = [r for r in rg if float(r[0].split("rho")[1]) <= 0.15]
        L.append("- **%s %s**: P1/P2/P4: %s; griglia %d/33 OK (fascia 0.06-0.15: %d/%d), profili con un dominio IC95 interamente < 0: %d/33 (fascia: %d). P4: %s" % (
            cand, title, "GO" if ok else "NO-GO", sum(r[1] for r in rg), sum(r[1] for r in band), len(band), sum(r[3] > 0 for r in rg), sum(r[3] > 0 for r in band),
            "; ".join("%s %s" % (d, f(b)) for d, b in zip(doms, rows[2][4]))))
L.append("")
for pn in ("P1", "P2", "P4"):
    gs = [M["%s|%s" % (d, pn)]["pol"]["strata_current"]["G_O_round"] for d in doms]
    L.append("**H1 no-go** (%s): G(O_round) di DraftPolicy default = %s → %s" % (
        pn, "; ".join("%s %s" % (d, g(x)) for d, x in zip(doms, gs)), "scatta" if all(x[0] < 0.03 for x in gs) else "non scatta"))
for pn in ("P1", "P2", "P4"):
    gs = [M["%s|%s" % (d, pn)]["pol"]["strata_cost_mtponly"]["G_O_depth"] for d in doms]
    L.append("**H4 no-go** (%s): G(O_depth) di STRATA_SPEC_COST=1 (solo MTP) = %s → %s" % (
        pn, "; ".join("%s %s" % (d, g(x)) for d, x in zip(doms, gs)), "scatta" if all(x[0] < 0.03 for x in gs) else "non scatta"))
L += ["", "## Profondità e classifica lungo rho_mtp (forma s(T) × rho_mtp)", "",
      "| forma | rho_mtp | dominio | k fisso migliore (argmax punto) | d MTP/round gate_v2 [IC95] | d strata_cost [IC95] | classifica (speedup, stime puntuali) | gate_v2 vs cost | gate_v2 vs Specu |", "|---|---|---|---|---|---|---|---|---|"]
for sn in SHAPES:
    for r in RHOS:
        for d in doms:
            c = G["%s|%s|rho%.4f" % (d, sn, r)]["pol"]; bk = G["%s|%s|rho%.4f" % (d, sn, r)]["best_fixed_k"]
            rk = sorted(("strata_current", "strata_cost", "specu", "specu_costdepth", "gate_v2", "mtp_fixed_k3"), key=lambda n: -c[n]["speedup"])
            L.append("| %s | %.3f | %s | %d | %s | %s | %s | %s | %s |" % (sn, r, d, bk, al(c["gate_v2"]["d_ci"]),
                     al(c["strata_cost"]["d_ci"]), " > ".join(rk), f(c["gate_v2"]["vs_cost"]), f(c["gate_v2"]["vs_specu"])))
open(os.path.join(out, "p4.md"), "w").write("\n".join(L) + "\n")
print("done", out, "%.0fs" % (time.time() - t0))
