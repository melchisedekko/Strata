"""BREAK-EVEN (d'') = MTP 3 draft + lookup <=11 token, T=12 verify rows (Lead conventions 08:06 CET: T = verify rows,
window[0]=x + T-1 drafts, generate.cpp L14922-14928; sfx.propose(S-1) L14897), vs (a') 3/7 (T=8, s(12)/s(8)) and
(a) 3/5 (T=6: --spec 4 default in setup.py L9420 -> spec 6 with lookup in generate.cpp L3208-3211; s(12)/s(6)).
AL; rho* and ratios PARAMETRIC (s(T)=1+rho(T-1), drafts free). Fixed in replay/run_breakeven_dsecond.json (519d09fb...).
Functions verbatim from lookup_rule_al_addendum.py (b402c026); loop/bootstrap as breakeven_dprime.py (71e8823d).
Lead go rule: soglia_go = 0.94 x s(12)/s(8) break-even, TUNE, gate, vs (a'), code and edit. usage: script OUTDIR"""
import json, os, sys, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strata_sim.postprocess import load_tf
from strata_sim.native import NativeSuffixDrafter

OUTD = sys.argv[1]; os.makedirs(OUTD, exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
RUNF = os.path.join(HERE, "run_breakeven_dsecond.json")
assert sha(RUNF) == "519d09fba57d682edd418082565d52824b010534113828531a4c2c3f250cfc33"
TR = "/workspace/strata-plus/traces/v1.1"
FILES = {"tune": os.path.join(TR, "tf_d7_p30.jsonl")}
for d in ("code", "chat", "edit"):
    FILES["holdout_" + d] = os.path.join(TR, "holdout_%s_tf_d7.jsonl" % d)
EXP = {"tune": "87efe507324b2a79b89c21a6736f1478094bf53385d9471694dc71b291d9abfa",
       "holdout_code": "a9e247b2fd9a0da14517459f028d2b9e85195955895855459c3c924f0e37f603",
       "holdout_chat": "b5380c42b9155571054958f00cb501ca7a309feaf8e9cc058f54bd00692b4588",
       "holdout_edit": "d9a48386945b1131766cb8b38a1572bc2d3992d8b5bd8291ecbe85c79f3e94ef"}
for k, p in FILES.items():
    assert sha(p) == EXP[k], k
OTHER = {"lookup_rule_al_addendum.py": "b402c026c5a1a5627590fa209e54b5f324ed8552e94b38aeca1ea0b3408f58d9",
         "breakeven_dprime.py": "71e8823da0741f382886f20f72fb42aad6fc2e44c2f6ce9077564aa8b02ee230",
         "run_breakeven_dprime.json": "beacb25e7aebf01e83c790cb8aecb268eba82ab5ff2fe181dee62fdc60fd7e24",
         "results/v2/breakeven_dprime/breakeven_dprime.json": "1da55ce52c8d17e195b03e3aa693d3d3bad228c9a6dd34ca0ac0fb78c9d37c55",
         "strata_sim/native.py": "6bc1af8e4987ce0384a3eb42214471fd24859251ff7c5ddb54da94ccd049a758",
         "strata_sim/postprocess.py": "02811133c6bf06e30c011dea5c5ec2b8972d3d781e2ae726d8948a865bd7be40",
         "native/libstrata_spec_capi.so": "8fb27b0d1ca6bfeb58d2e9a1a45d28cc779f1feb7ef1662b2eb6d524608b055b"}
for k, v in OTHER.items():
    assert sha(os.path.join(HERE, k)) == v, k
PREV = json.load(open(os.path.join(HERE, "results/v2/breakeven_dprime/breakeven_dprime.json")))
_src = open(os.path.join(HERE, "lookup_rule_al_addendum.py")).read()
COLS = {"a": (3, 5), "ap": (3, 7), "ds": (3, 11), "dp": (3, 12)}
MIN_P = 0.5
B, SEED = 2000, 0
GRID = np.arange(0, 2.0 + 1e-12, 0.0005)
GO = 0.94


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


_mine = open(os.path.abspath(__file__)).read()
_fa = _src[_src.index("def prompts"):_src.index("RATIO =")].rstrip()
assert _fa in _mine, "functions not verbatim"

RATIOS = {"ap": {"s12/s8": lambda r: (1 + 11 * r) / (1 + 7 * r)}, "a": {"s12/s6": lambda r: (1 + 11 * r) / (1 + 5 * r)}}
OUT = {"label": "proxy CPU, AL, parametrico: (d'') MTP 3 + lookup<=11, T=12 righe; rho* e rapporti PARAMETRICI (s(T)=1+rho(T-1), draft a costo zero), non misurati",
       "run_file_sha256": sha(RUNF), "script_sha256": sha(os.path.abspath(__file__)), "files_sha256": {k: sha(p) for k, p in FILES.items()},
       "columns": COLS, "T_rows": {"a": 6, "ap": 8, "ds": 12}, "results": {}, "checks": {}, "dsecond_minus_dprime": {}}
rng = np.random.default_rng(SEED)
cache = {}
ci = lambda v: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))


def pair(A, S, v, x, base):
    xx, bb = A[(v, x)], A[(v, base)]
    pt, pm = rho_star(bb["R"].sum(), bb["X"].sum(), xx["R"].sum(), xx["X"].sum())
    bt, bm = rho_star(bb["R"][S].sum(1), bb["X"][S].sum(1), xx["R"][S].sum(1), xx["X"][S].sum(1))
    dR = bb["R"].sum() - xx["R"].sum(); dX = xx["X"].sum() - bb["X"].sum()
    cf = "mai" if dR <= 0 else (">2" if dX <= 0 or dR / dX > 2 else float(dR / dX))
    p = fmt_rho(pt[0], pm[0])
    lo, hi = float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))
    ent = dict(point=p, closed_form=cf, ci95=[lo, hi], frac_boot_gt2=float(np.mean(~np.isfinite(bt))), frac_boot_mai=float(np.mean(bm)),
               breakeven_exists=bool(dR > 0 and dX > 0), dR_base_minus_x=float(dR), dX_x_minus_base=float(dX), ratios={})
    for name, f in RATIOS[base].items():
        rr = lambda r: (float(f(r)) if np.isfinite(r) else ">%.4f" % f(2.0))
        ent["ratios"][name] = dict(point=(float(f(p)) if isinstance(p, float) else (p if p == "mai" else ">%.4f" % f(2.0))),
                                   ci95=[rr(lo) if not (np.mean(bm) > 0.025 and lo == 0.0) else float(f(0.0)), rr(hi)],
                                   max_by_construction_rho_inf=float(f(1e12)), at_rho_2=float(f(2.0)))
    return ent


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
        clusters = [q["session"] for q in reqs]; keys = sorted(set(clusters))
        g_idx = {k: [j for j, x in enumerate(clusters) if x == k] for k in keys}
        A = {kk: {f: np.array([sum(rows[kk][j][f] for j in g_idx[k]) for k in keys], float) for f in ("N", "R", "X", "LR", "LTOK")} for kk in rows}
        S = rng.integers(0, len(keys), (B, len(keys)))
        AL = {kk: A[kk]["N"].sum() / A[kk]["R"].sum() for kk in A}
        ALb = {kk: A[kk]["N"][S].sum(1) / A[kk]["R"][S].sum(1) for kk in A}
        pv = PREV["results"][key]
        for v in ("oracle", "gate"):
            for c in ("a", "ap", "dp"):
                ref = pv["AL"][v][c]
                assert AL[(v, c)] == ref[0] and tuple(ci(ALb[(v, c)])) == tuple(ref[1:]), (key, v, c)
            for base in ("ap", "a"):
                e = pair(A, S, v, "dp", base); r0 = pv["rho"]["%s|dp_vs_%s" % (v, base)]
                assert e["point"] == r0["point"] and e["ci95"] == r0["ci95"] and e["closed_form"] == r0["closed_form"], (key, v, base)
                for nm in e["ratios"]:
                    assert e["ratios"][nm]["point"] == r0["ratios"][nm]["point"] and e["ratios"][nm]["ci95"] == r0["ratios"][nm]["ci95"], (key, v, base, nm)
        OUT["checks"][key] = dict(a_ap_AL_ci_equal_breakeven_dprime=True, dprime_reproduced_AL_ci_rho_ratios=True, lookup16_vs_trace_cap7_mismatch=mism)
        res = dict(n_req=len(reqs), AL={}, R_X={}, rho={})
        for v in ("oracle", "gate"):
            res["AL"][v] = {c: (float(AL[(v, c)]),) + ci(ALb[(v, c)]) for c in ("a", "ap", "ds")}
            res["R_X"][v] = {c: dict(N=float(A[(v, c)]["N"].sum()), R=float(A[(v, c)]["R"].sum()), X=float(A[(v, c)]["X"].sum())) for c in ("a", "ap", "ds", "dp")}
            for base in ("ap", "a"):
                res["rho"]["%s|ds_vs_%s" % (v, base)] = pair(A, S, v, "ds", base)
        res["capture_gate"] = (float(AL[("gate", "ds")] / AL[("oracle", "ds")]),) + ci(ALb[("gate", "ds")] / ALb[("oracle", "ds")])
        LR = A[("gate", "ds")]["LR"].sum()
        res["lookup_branch_gate"] = dict(share_rounds=float(LR / A[("gate", "ds")]["R"].sum()), mean_tokens_when_lookup=float(A[("gate", "ds")]["LTOK"].sum() / LR) if LR else None)
        dd = {}
        for v in ("oracle", "gate"):
            dd[v] = dict(AL_ds=float(AL[(v, "ds")]), AL_dp=float(AL[(v, "dp")]), dAL=float(AL[(v, "ds")] - AL[(v, "dp")]),
                         dAL_rel=(float(AL[(v, "ds")] / AL[(v, "dp")] - 1),) + ci(ALb[(v, "ds")] / ALb[(v, "dp")] - 1),
                         dR=float(A[(v, "ds")]["R"].sum() - A[(v, "dp")]["R"].sum()), dX=float(A[(v, "ds")]["X"].sum() - A[(v, "dp")]["X"].sum()),
                         rho_ds_vs_ap=res["rho"]["%s|ds_vs_ap" % v]["point"], rho_dp_vs_ap=pv["rho"]["%s|dp_vs_ap" % v]["point"],
                         rho_ds_vs_a=res["rho"]["%s|ds_vs_a" % v]["point"], rho_dp_vs_a=pv["rho"]["%s|dp_vs_a" % v]["point"])
        OUT["dsecond_minus_dprime"][key] = dd
        OUT["results"][key] = res
        print(key, "mism", mism, {v: {c: round(x[0], 4) for c, x in res["AL"][v].items()} for v in res["AL"]},
              {k: (v["point"], {n: r["point"] for n, r in v["ratios"].items()}) for k, v in res["rho"].items()}, flush=True)

go = {}
for dom in ("code", "edit"):
    for v, role in (("gate", "decisionale"), ("oracle", "lettura secondaria")):
        r = OUT["results"]["tune|" + dom]["rho"]["%s|ds_vs_ap" % v]["ratios"]["s12/s8"]
        p = r["point"]
        go["%s|%s" % (dom, v)] = dict(role=role, breakeven_s12_s8=p, breakeven_ci95=r["ci95"],
                                      soglia_go=(GO * p if isinstance(p, float) else "non definita (%s)" % p))
OUT["go_threshold"] = dict(rule="soglia_go = 0.94 x pareggio s(12)/s(8), tune, (d'') vs (a'); gate decisionale, oracolo secondario", values=go)
print(json.dumps(go, indent=1))
json.dump(OUT, open(os.path.join(OUTD, "breakeven_dsecond.json"), "w"), indent=1, default=float)
