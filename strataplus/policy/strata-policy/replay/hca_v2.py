"""H-CA eval v2: run_hca.json + run_hca_addendum1.json (lettura decisionale cross-fitted a 5 fold, verdetti per rho).
Riusa per import le funzioni di hca.py (invariato). Output SOLO aggregati (licenza: niente id, token, testo, linguaggi).
  smoke OUT.json            : sha + caricamento + forme (nessuna metrica), output in /tmp
  eval OUTDIR --authorized  : valutazione completa, scrive OUTDIR/hca_results.json (aggregati)
Proxy CPU (tracce v1.1, Qwen3.5-2B-MTP); tok/s STIMATI s(T)=1+rho(T-1), draft a costo zero."""
import json, os, sys, time, hashlib, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
SHAS = {"run_hca.json": "ea2bed9c1438175c279c291652a6e9dd552e14b24d694320befc9338249bf50b",
        "run_hca_addendum1.json": "c3490e220313ec377e0fbc0f63f0994a228d351d0286b9248ec125a81726c386",
        "hca.py": "35ddc537b0306780ceb3d920476d64d1530eec097a55a53f5b3aacbf928ed348"}
for f, h in SHAS.items(): assert sha(os.path.join(HERE, f)) == h, f
import hca
from hca import GRID, RHO, DOMAINS, NFOLD, MAXA, THETA_LK, THETA_P, FILES, Pol, run, feats, tokps, boot, round_oracle, seg_oracle

EPS = 1e-15


def ratio(rows): return sum(r[0] for r in rows) / sum(r[1] for r in rows)
def al(rows): return sum(r[0] for r in rows) / sum(r[2] for r in rows)


def walk_table(q, rho, pick_cell, table):
    """walk con configurazione = table[cella]; ritorna (N,C,R), insieme celle visitate, conteggio round per cella."""
    vis = collections.Counter()
    def pick(qq, i, hist):
        c = pick_cell(qq, i, hist); vis[c] += 1; return table[c]
    N, C, R, _ = run(q, rho, pick, Pol(8))
    return (N, C, R), vis


def ascent(Q, rho, pick_cell, ncell, init, cands, passes=2):
    """ascesa per coordinate esatta: dopo un cambio in una cella si rigiocano solo le richieste che l'hanno visitata
    (la walk legge la tabella solo nelle celle visitate: deterministica). Punteggio = sum N / sum C in ordine fisso."""
    tab = list(init); res = [walk_table(q, rho, pick_cell, tab) for q in Q]
    score = lambda rs: sum(r[0][0] for r in rs) / sum(r[0][1] for r in rs)
    cur = score(res)
    for _ in range(passes):
        for cell in range(ncell):
            for a in cands:
                if a == tab[cell]: continue
                t2 = list(tab); t2[cell] = a
                r2 = [walk_table(q, rho, pick_cell, t2) if res[j][1][cell] else res[j] for j, q in enumerate(Q)]
                s2 = score(r2)
                if s2 > cur + EPS: tab, cur, res = t2, s2, r2
    return tab, cur


def fit_cls(Q, rho, A, base):
    best = None
    for th in [(a, b) for a in THETA_LK for b in THETA_P]:
        tab, cur = ascent(Q, rho, lambda q, i, h, th=th: feats(q, i, h, *th), 16, [base] * 16, A)
        if best is None or cur > best[0] + EPS: best = (cur, th, tab)
    return best[1], best[2]


def cls_run(q, rho, th, tab): return walk_table(q, rho, lambda qq, i, h: feats(qq, i, h, *th), tab)
def seg_pick(q, i, h): return int(q["in_code"][i])
def best_fixed(W, ix): return max(range(len(GRID)), key=lambda g: (ratio([W[j][g] for j in ix]), -g))


def select(tune, W, SEGCH, rho, train):
    """tutte le scelte sulle richieste 'train' (indici nella lista tune)."""
    g1 = best_fixed(W, train); out = {"g1": g1, "g2": {}, "t3": {}}
    for d in DOMAINS:
        ix = [j for j in train if tune[j]["domain"] == d]
        out["g2"][d] = best_fixed(W, ix) if ix else g1
        if ix:
            tab, _ = ascent([tune[j] for j in ix], rho, seg_pick, 2, [GRID[out["g2"][d]]] * 2, GRID)
            out["t3"][d] = tab
        else: out["t3"][d] = [GRID[g1]] * 2
    cnt = collections.Counter(c for j in train for c in SEGCH[j])
    A = sorted(cnt, key=lambda c: (-cnt[c], GRID.index(c)))[:MAXA]
    if GRID[g1] not in A: A.append(GRID[g1])
    out["A"] = A; out["th"], out["tab"] = fit_cls([tune[j] for j in train], rho, A, GRID[g1])
    return out


def apply(q, j, W, sel, rho):
    d = q["domain"]; r3, _ = walk_table(q, rho, seg_pick, sel["t3"][d]); rc, vis = cls_run(q, rho, sel["th"], sel["tab"])
    return {"1": W[j][sel["g1"]], "2c": W[j][sel["g2"][d]], "3c": r3, "cls": rc}, vis


def dom_block(Q, ix, arms, oracles):
    e = {"n_req": len(ix), "N": int(sum(Q[j]["n"] for j in ix)), "tokps": {}, "AL": {}, "ci95_vs_1": {}}
    for k, rows in arms.items():
        rr = [rows[j] for j in ix]; e["tokps"][k] = ratio(rr); e["AL"][k] = al(rr)
    for k, rows in oracles.items(): e["tokps"][k] = ratio([rows[j] for j in ix])
    return e


def evaluate(outdir):
    t0 = time.time(); os.makedirs(outdir, exist_ok=True)
    assert not os.path.exists(os.path.join(outdir, "hca_results.json"))
    voc = hca.Vocab(); D = {k: hca.load(k, voc) for k in FILES}; tune = D["tune"]
    folds = [q["idx"] % NFOLD for q in tune]
    res = {"label": "H-CA, PROXY CPU (tracce v1.1, Qwen3.5-2B-MTP), tok/s STIMATI s(T)=1+rho(T-1), draft a costo zero; solo aggregati",
           "inputs_sha256": dict(SHAS, **{"traces/" + v[0]: v[1] for v in FILES.values()}, MANIFEST=hca.MANIFEST_SHA),
           "counts": {"tune_req_domain_fold": {d: [sum(1 for j, q in enumerate(tune) if q["domain"] == d and folds[j] == f)
                                                  for f in range(NFOLD)] for d in DOMAINS},
                      "segments": {k: {d: int(sum(len(q["bounds"]) + 1 for q in Q if q["domain"] == d)) for d in DOMAINS} for k, Q in D.items()},
                      "requests": {k: {d: sum(1 for q in Q if q["domain"] == d) for d in DOMAINS} for k, Q in D.items()},
                      "positions": {k: {d: int(sum(q["n"] for q in Q if q["domain"] == d)) for d in DOMAINS} for k, Q in D.items()}},
           "scen": {}, "timing_s": {}}
    for sc, rho in RHO.items():
        W = {k: [[hca.fixed_walk(q, g, rho) for g in GRID] for q in Q] for k, Q in D.items()}
        SEG = {k: [seg_oracle(q, rho, GRID) for q in Q] for k, Q in D.items()}
        SEGCH = [ch for _, ch in SEG["tune"]]
        ORA = {k: {"oracle_req": [max(w, key=lambda x: x[0] / x[1]) for w in W[k]], "oracle_seg": [s[0] for s in SEG[k]],
                   **{"round_" + l: [round_oracle(q, rho, tm, lm) for q in Q] for l, tm, lm in (("R01", 8, 7), ("P", 12, 11), ("X", 16, 15))},
                   "round_greedy_R01": [round_oracle(q, rho, 8, 7, dp=False) for q in Q]} for k, Q in D.items()}
        # cross-fit sul tune
        CF = [None] * len(tune); cell_cf = {d: [0] * 16 for d in DOMAINS}; fold_sel = []
        for f in range(NFOLD):
            train = [j for j in range(len(tune)) if folds[j] != f]; sel = select(tune, W["tune"], SEGCH, rho, train)
            fold_sel.append({"arm1": list(GRID[sel["g1"]]), "arm2c": {d: list(GRID[g]) for d, g in sel["g2"].items()},
                             "arm3c": {d: [list(c) for c in t] for d, t in sel["t3"].items()}, "A_size": len(sel["A"]),
                             "theta": list(sel["th"])})
            for j in range(len(tune)):
                if folds[j] == f:
                    CF[j], vis = apply(tune[j], j, W["tune"], sel, rho)
                    for c, v in vis.items(): cell_cf[tune[j]["domain"]][c] += v
        full = select(tune, W["tune"], SEGCH, rho, list(range(len(tune))))
        r0 = [g for g in GRID if g[:2] == GRID[full["g1"]][:2] and g[2] != "cost"] if GRID[full["g1"]][2] != "cost" else []
        out = {"rho": rho, "folds": fold_sel,
               "full_tune_selection": {"arm1": list(GRID[full["g1"]]), "arm2c": {d: list(GRID[g]) for d, g in full["g2"].items()},
                                       "arm3c": {d: [list(c) for c in t] for d, t in full["t3"].items()},
                                       "A": [list(c) for c in full["A"]], "theta": list(full["th"]), "table": [list(c) for c in full["tab"]]},
               "cells_rounds_tune_cf": cell_cf, "cells_rounds_insample": {}, "dom": {}}
        for k, Q in D.items():
            INS = [None] * len(Q); cell_in = {d: [0] * 16 for d in DOMAINS}
            for j, q in enumerate(Q):
                INS[j], vis = apply(q, j, W[k], full, rho)
                for c, v in vis.items(): cell_in[q["domain"]][c] += v
            out["cells_rounds_insample"][k] = cell_in
            R0 = [seg_oracle(q, rho, r0)[0] if r0 else None for q in Q]
            for d in DOMAINS:
                ix = [j for j, q in enumerate(Q) if q["domain"] == d]
                if not ix: continue
                arms = {"%s_ins" % a: [INS[j][a] for j in range(len(Q))] for a in ("1", "2c", "3c", "cls")}
                if k == "tune": arms.update({"%s_cf" % a: [CF[j][a] for j in range(len(Q))] for a in ("1", "2c", "3c", "cls")})
                arms.update({"oracle_req": ORA[k]["oracle_req"], "oracle_seg": ORA[k]["oracle_seg"]})
                ors = {kk: v for kk, v in ORA[k].items() if kk.startswith("round")}
                if r0: ors["oracle_seg_R0only"] = R0
                e = dom_block(Q, ix, arms, ors)
                base = "1_cf" if k == "tune" else "1_ins"
                for a in arms:
                    if a != base: e["ci95_vs_1"][a] = boot([arms[a][j] for j in ix], [arms[base][j] for j in ix])
                e["base"] = base; t = e["tokps"]
                b2 = "2c_cf" if k == "tune" else "2c_ins"; bc = "cls_cf" if k == "tune" else "cls_ins"; b3 = "3c_cf" if k == "tune" else "3c_ins"
                e["gain_2c"] = t[b2] / t[base] - 1
                e["gain_3c"] = t[b3] / t[base] - 1
                e["gain_cls"] = t[bc] / t[base] - 1
                e["gain_oracle_req_ceiling"] = t["oracle_req"] / t[base] - 1
                e["capture_cls_of_2c"] = (t[bc] - t[base]) / (t[b2] - t[base]) if t[b2] != t[base] else None
                e["capture_cls_of_oracle_req"] = (t[bc] - t[base]) / (t["oracle_req"] - t[base]) if t["oracle_req"] != t[base] else None
                out["dom"]["%s/%s" % (k, d)] = e
        T = {d: out["dom"]["tune/" + d] for d in DOMAINS}
        falls = all(T[d]["gain_2c"] < 0.03 for d in DOMAINS)
        elig = [d for d in DOMAINS if T[d]["gain_2c"] >= 0.03]
        cls_v = "non applicabile" if not elig else ("NO-GO" if all((T[d]["capture_cls_of_2c"] or 0) < 0.5 for d in elig) else "GO")
        out["verdict"] = {"H-CA": "scende" if falls else "regge", "domini_sopra_3pct": elig, "classificatore": cls_v}
        res["scen"][sc] = out; res["timing_s"][sc] = round(time.time() - t0, 1)
        print(sc, out["verdict"], res["timing_s"][sc], flush=True)
    v = {k: [res["scen"][s]["verdict"][k] for s in RHO] for k in ("H-CA", "classificatore")}
    res["verdict"] = {k: (x[0] if x[0] == x[1] else "dipende dall'hardware") for k, x in v.items()}
    res["verdict"]["per_rho"] = {s: res["scen"][s]["verdict"] for s in RHO}
    json.dump(res, open(os.path.join(outdir, "hca_results.json"), "x"), indent=1, default=str)


def smoke(out):
    voc = hca.Vocab(); S = {"label": "smoke hca_v2: sha e forme, nessuna metrica", "shas_ok": True, "files": {}}
    for k in FILES:
        Q = hca.load(k, voc)
        S["files"][k] = {"requests": len(Q), "domains": dict(collections.Counter(q["domain"] for q in Q)),
                         "folds": dict(collections.Counter(q["idx"] % NFOLD for q in Q))}
    p = Pol(8); assert len(p.clone().log) == 0
    json.dump(S, open(out, "w"), indent=1); print(json.dumps(S))


if __name__ == "__main__":
    if sys.argv[1] == "smoke":
        assert sys.argv[2].startswith("/tmp/"); smoke(sys.argv[2])
    elif sys.argv[1] == "eval":
        assert "--authorized" in sys.argv; evaluate(sys.argv[2])
    else: sys.exit(2)
