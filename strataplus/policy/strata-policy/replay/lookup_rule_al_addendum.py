"""ADDENDUM C+D to the lookup-rule study (Strata Lead 07:02 CET): AL only, DESCRIPTIVE; rho* and break-even ratios PARAMETRIC.
Fixed in replay/run_lookup_rule_addendum.json (sha256 f151f985..., written read-only before computing) which refers to
replay/run_lookup_rule.json (43785c4b...).  Functions copied verbatim from replay/lookup_rule_al.py (prompts, walk_oracle,
walk_rule, rho_star, fmt_rho).  New column a' = MTP 3 drafts + standalone lookup <=7 (= --spec 4 --lookup-chain 2 without
the chained lookup).  usage: script OUTDIR"""
import json, os, sys, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strata_sim.postprocess import load_tf
from strata_sim.native import NativeSuffixDrafter

OUTD = sys.argv[1]; os.makedirs(OUTD, exist_ok=True)
TR = "/workspace/strata-plus/traces/v1.1"
FILES = {"tune": os.path.join(TR, "tf_d7_p30.jsonl")}
for d in ("code", "chat", "edit"):
    FILES["holdout_" + d] = os.path.join(TR, "holdout_%s_tf_d7.jsonl" % d)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
ADDF = os.path.join(HERE, "run_lookup_rule_addendum.json"); RUNF = os.path.join(HERE, "run_lookup_rule.json")
assert sha(ADDF) == "f151f9852e0fd551c44ff3d13a864613006b75b901c1ac201f60268fbe370a64"
assert sha(RUNF) == "43785c4ba35f44a3824064ce972b4eaba48ffaa68adede7a847ea7df070daec2"
PREVF = os.path.join(HERE, "results/v2/ceiling_installed_cfg/ceiling_installed_cfg.json")
assert sha(PREVF) == "da1f9a1f1bb420740ea955c0c8fad7113dd64d8f3f00e80f91fd51826b6849c0"
PREV = json.load(open(PREVF))
MAINF = os.path.join(HERE, "results/v2/lookup_rule_al/lookup_rule_al.json")
MAIN = json.load(open(MAINF))
COLS = {"a": (3, 5), "ap": (3, 7), "b": (7, 7), "d": (7, 12), "c": (7, 16)}
MIN_P = 0.5
B, SEED = 2000, 0
GRID = np.arange(0, 2.0 + 1e-12, 0.0005)


def prompts(path):
    P = {}
    for l in open(path):
        o = json.loads(l)
        if o.get("type") == "request" and o.get("rep", 0) == 0:
            P[o["req_id"]] = o["prompt_ids"]
    return P


def walk_oracle(q, acc16, k16, mcap, lcap):
    n = q["n"]; i = 0; R = 0; X = 0
    while i < n:
        am = min(int(q["mtp_acc"][i]), mcap); al = min(int(acc16[i]), lcap); cap = n - i - 1
        a = min(max(am, al), cap)
        if min(al, cap) == a:          # tie -> lookup (ceiling_installed_cfg)
            T = 1 + min(int(k16[i]), lcap)
        else:
            T = 1 + mcap
        T = min(T, n - i)
        R += 1; X += T - 1; i += a + 1
    return dict(N=n, R=R, X=X, LR=0, LTOK=0)


def walk_rule(q, acc16, k16, tok0, mcap, lcap, gate):
    n = q["n"]; i = 0; R = 0; X = 0; LR = 0; LTOK = 0; S_mtp = mcap + 1
    while i < n:
        take = k16[i] > 0 and (not gate or int(tok0[i]) == int(q["mtp_tok"][i][0]))
        if take:
            T = min(1 + min(int(k16[i]), lcap), n - i)
            a = min(int(acc16[i]), T - 1)
        else:
            pr = q["mtp_p"][i]; run = 0
            while run < len(pr) and pr[run] >= MIN_P:
                run += 1
            T = min(min(S_mtp, 1 + run), n - i)
            a = int(min(q["mtp_acc"][i], T - 1, n - i - 1))
        R += 1; X += T - 1; i += a + 1
        if take:
            LR += 1; LTOK += a + 1
    return dict(N=n, R=R, X=X, LR=LR, LTOK=LTOK)


def agg(rows, idx):
    return {k: np.array([[r[k] for r in rows][j] for j in idx], float) for k in ("N", "R", "X", "LR", "LTOK")}


def rho_star(Ra, Xa, Rx, Xx):
    """vectorised over replicates: f(rho) = M_x/M_a - 1 sign = sign((Ra + rho Xa) - (Rx + rho Xx)) (N equal).
    grid + 40-step bisection on the first sign change; inf = '>2', 0 with flag = 'mai'."""
    Ra, Xa, Rx, Xx = map(np.atleast_1d, (Ra, Xa, Rx, Xx))
    f = lambda r: (Ra[:, None] + r * Xa[:, None]) - (Rx[:, None] + r * Xx[:, None])
    F = f(GRID[None, :])
    mai = F[:, 0] <= 0
    neg = F <= 0
    first = np.where(neg.any(1), neg.argmax(1), -1)
    out = np.full(len(Ra), np.inf)
    for j in np.where((~mai) & (first > 0))[0]:
        lo, hi = GRID[first[j] - 1], GRID[first[j]]
        g = lambda r: (Ra[j] + r * Xa[j]) - (Rx[j] + r * Xx[j])
        for _ in range(40):
            m = 0.5 * (lo + hi)
            lo, hi = (m, hi) if g(m) > 0 else (lo, m)
        out[j] = 0.5 * (lo + hi)
    out[mai] = 0.0
    return out, mai


def fmt_rho(v, mai):
    return "mai" if mai else (">2" if not np.isfinite(v) else float(v))



RATIO = {"c": lambda r: (1 + 15 * r) / (1 + 7 * r), "d": lambda r: (1 + 11 * r) / (1 + 7 * r)}
OUT = {"label": "ADDENDUM C+D: colonna a' (MTP 3, lookup<=7) e rapporti di pareggio s(16)/s(8), s(12)/s(8): PARAMETRICI "
                "(s(T)=1+rho(T-1), draft a costo zero), non misurati; solo AL",
       "addendum_sha256": sha(ADDF), "run_file_sha256": sha(RUNF), "main_json_sha256": sha(MAINF),
       "script_sha256": sha(os.path.abspath(__file__)), "files_sha256": {k: sha(p) for k, p in FILES.items()},
       "columns": COLS, "results": {}}
rng = np.random.default_rng(SEED)
cache = {}
for dom in ("code", "chat", "edit"):
    for split in ("tune", "holdout"):
        path = FILES["tune"] if split == "tune" else FILES["holdout_" + dom]
        if path not in cache:
            cache[path] = (load_tf(path), prompts(path))
        Rq, P = cache[path]
        reqs = [q for q in Rq if q["domain"] == dom]
        key = "%s|%s" % (split, dom)
        rows = {}; mism = 0
        for q in reqs:
            y = q["y"]
            lk = NativeSuffixDrafter(3, 64, 1 << 15); lk.append(np.asarray(P[q["req"]], np.int32))
            k16, _, acc16, tok = lk.scan(y, 16, want_tokens=True)
            tok0 = tok[:, 0]
            mism += int(np.sum(np.minimum(acc16, 7) != q["lk_acc"]))
            for c, (mc, lc) in COLS.items():
                rows.setdefault(("oracle", c), []).append(walk_oracle(q, acc16, k16, mc, lc))
                rows.setdefault(("gate", c), []).append(walk_rule(q, acc16, k16, tok0, mc, lc, True))
                rows.setdefault(("nogate", c), []).append(walk_rule(q, acc16, k16, tok0, mc, lc, False))
        clusters = [q["session"] for q in reqs]; keys = sorted(set(clusters))
        g_idx = {k: [j for j, x in enumerate(clusters) if x == k] for k in keys}
        A = {kk: {f: np.array([sum(rows[kk][j][f] for j in g_idx[k]) for k in keys], float) for f in ("N", "R", "X", "LR", "LTOK")} for kk in rows}
        S = rng.integers(0, len(keys), (B, len(keys)))
        AL = {kk: A[kk]["N"].sum() / A[kk]["R"].sum() for kk in A}
        ALb = {kk: A[kk]["N"][S].sum(1) / A[kk]["R"][S].sum(1) for kk in A}
        ci = lambda v: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))
        # checks: columns a,b,d,c reproduce the main run (oracle + rule) and ceiling_installed_cfg (oracle)
        for c in ("a", "b", "d", "c"):
            assert AL[("oracle", c)] == PREV["results"][key]["AL"][c], (key, c)
            for v in ("oracle", "gate", "nogate"):
                assert AL[(v, c)] == MAIN["results"][key]["AL"]["%s|%s" % (v, c)][0], (key, v, c)
        res = dict(n_req=len(reqs), lookup16_vs_trace_cap7_mismatch=mism, checks_reproduce_main_and_ceiling=True,
                   AL={}, decomposition={}, lookup_branch_ap={}, rho={})
        for v in ("oracle", "gate", "nogate"):
            res["AL"]["%s|ap" % v] = (float(AL[(v, "ap")]),) + ci(ALb[(v, "ap")])
            if v != "oracle":
                res["AL"]["%s|ap_capture" % v] = (float(AL[(v, "ap")] / AL[("oracle", "ap")]),) + ci(ALb[(v, "ap")] / ALb[("oracle", "ap")])
                LR = A[(v, "ap")]["LR"].sum()
                res["lookup_branch_ap"][v] = dict(share_rounds=float(LR / A[(v, "ap")]["R"].sum()),
                                                  mean_tokens_when_lookup=float(A[(v, "ap")]["LTOK"].sum() / LR) if LR else None)
            a_, ap, b_ = (v, "a"), (v, "ap"), (v, "b")
            with np.errstate(invalid="ignore", divide="ignore"):
                sh = (ALb[ap] - ALb[a_]) / (ALb[b_] - ALb[a_])
            shf = sh[np.isfinite(sh)]
            den = AL[b_] - AL[a_]
            res["decomposition"][v] = dict(
                total_b_vs_a=(float(AL[b_] / AL[a_] - 1),) + ci(ALb[b_] / ALb[a_] - 1),
                lookup_only_ap_vs_a=(float(AL[ap] / AL[a_] - 1),) + ci(ALb[ap] / ALb[a_] - 1),
                wider_mtp_b_vs_ap=(float(AL[b_] / AL[ap] - 1),) + ci(ALb[b_] / ALb[ap] - 1),
                share_gain_lookup=(float((AL[ap] - AL[a_]) / den) if den != 0 else None,) +
                                  ((float(np.percentile(shf, 2.5)), float(np.percentile(shf, 97.5))) if len(shf) else (None, None)),
                share_gain_mtp=(float((AL[b_] - AL[ap]) / den) if den != 0 else None,) +
                               ((float(np.percentile(1 - shf, 2.5)), float(np.percentile(1 - shf, 97.5))) if len(shf) else (None, None)))
            for x in ("c", "d"):
                for base in ("b", "a", "ap"):
                    bb, xx = A[(v, base)], A[(v, x)]
                    pt, pm = rho_star(bb["R"].sum(), bb["X"].sum(), xx["R"].sum(), xx["X"].sum())
                    bt, bm = rho_star(bb["R"][S].sum(1), bb["X"][S].sum(1), xx["R"][S].sum(1), xx["X"][S].sum(1))
                    dR = bb["R"].sum() - xx["R"].sum(); dX = xx["X"].sum() - bb["X"].sum()
                    cf = "mai" if dR <= 0 else (">2" if dX <= 0 or dR / dX > 2 else float(dR / dX))
                    p = fmt_rho(pt[0], pm[0])
                    lo, hi = float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))
                    f = RATIO[x]
                    rr = lambda r: (float(f(r)) if np.isfinite(r) else ">%.4f" % f(2.0))
                    res["rho"]["%s|%s_vs_%s" % (v, x, base)] = dict(
                        point=p, closed_form=cf, ci95=[lo, hi], frac_boot_gt2=float(np.mean(~np.isfinite(bt))),
                        frac_boot_mai=float(np.mean(bm)),
                        ratio_name="s16/s8" if x == "c" else "s12/s8",
                        ratio_point=(float(f(p)) if isinstance(p, float) else (p if p == "mai" else ">%.4f" % f(2.0))),
                        ratio_ci95=[rr(lo) if not (np.mean(bm) > 0.025 and lo == 0.0) else float(f(0.0)), rr(hi)],
                        R_base=float(bb["R"].sum()), X_base=float(bb["X"].sum()), R_x=float(xx["R"].sum()), X_x=float(xx["X"].sum()))
                    if base == "a":
                        assert res["rho"]["%s|%s_vs_a" % (v, x)]["point"] == MAIN["results"][key]["rho_star"]["%s|%s_vs_a" % (v, x)]["point"]
        OUT["results"][key] = res
        print(key, "mism", mism, {k: round(v[0], 4) for k, v in res["AL"].items()},
              {k: (v["point"], v["ratio_point"]) for k, v in res["rho"].items() if "_vs_b" in k}, flush=True)
json.dump(OUT, open(os.path.join(OUTD, "lookup_rule_al_addendum.json"), "w"), indent=1, default=float)
