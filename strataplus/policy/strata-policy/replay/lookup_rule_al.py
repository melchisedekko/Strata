"""LOOKUP RULE min(match,16) vs ORACLE (Strata Lead 06:58 + additions 06:59 CET): AL only, DESCRIPTIVE, offline.
Everything is fixed in replay/run_lookup_rule.json (sha256 43785c4b..., written read-only before any computation).
Rule: if the production SuffixDrafter proposes a non-empty candidate (k16>0; y never used to decide) -> propose
min(k16, L_col) tokens; else the installed default = MTP with --spec-min-p 0.5 (DefaultMinP of
holdout_v11_speccost_vs_default.py 6809946d, without its DraftPolicy lookup part), MTP cap of the column.
Variants: with engine gate sbuf[0]==drafts[0] (generate.cpp L14899; fail -> MTP branch) and without.
Oracle = ceiling_installed_cfg walk (asserted bit-for-bit).  rho*: PARAMETRIC s(T)=1+rho(T-1), drafts free.
usage: script OUTDIR"""
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
RUNF = os.path.join(HERE, "run_lookup_rule.json")
assert sha(RUNF) == "43785c4ba35f44a3824064ce972b4eaba48ffaa68adede7a847ea7df070daec2"
PREV = json.load(open(os.path.join(HERE, "results/v2/ceiling_installed_cfg/ceiling_installed_cfg.json")))
assert sha(os.path.join(HERE, "results/v2/ceiling_installed_cfg/ceiling_installed_cfg.json")) == \
    "da1f9a1f1bb420740ea955c0c8fad7113dd64d8f3f00e80f91fd51826b6849c0"
COLS = {"a": (3, 5), "b": (7, 7), "d": (7, 12), "c": (7, 16)}   # (MTP drafts, lookup tokens)
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


OUT = {"label": "REGOLA min(match,16) vs ORACOLO: solo AL, descrittivo; rho* PARAMETRICO (s(T)=1+rho(T-1), draft a costo zero), non misurato",
       "run_file_sha256": sha(RUNF), "script_sha256": sha(os.path.abspath(__file__)),
       "files_sha256": {k: sha(p) for k, p in FILES.items()}, "columns": COLS, "results": {}}
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
        rows = {}; tfpos = dict(n=0, match=0, match_gate=0); mism = 0
        for q in reqs:
            y = q["y"]; n = q["n"]
            lk = NativeSuffixDrafter(3, 64, 1 << 15); lk.append(np.asarray(P[q["req"]], np.int32))
            k16, _, acc16, tok = lk.scan(y, 16, want_tokens=True)
            tok0 = tok[:, 0]
            mism += int(np.sum(np.minimum(acc16, 7) != q["lk_acc"]))
            g = np.array([int(tok0[i]) == int(q["mtp_tok"][i][0]) for i in range(n)])
            tfpos["n"] += n; tfpos["match"] += int(np.sum(k16 > 0)); tfpos["match_gate"] += int(np.sum((k16 > 0) & g))
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
        res = dict(n_req=len(reqs), positions=tfpos, lookup16_vs_trace_cap7_mismatch=mism, AL={}, capture={}, delta={},
                   lookup_branch={}, rho_star={})
        for kk in A:
            res["AL"]["%s|%s" % kk] = (float(AL[kk]),) + ci(ALb[kk])
        # oracle reproduces ceiling_installed_cfg exactly
        for c in COLS:
            assert AL[("oracle", c)] == PREV["results"][key]["AL"][c], (key, c)
        res["oracle_reproduces_ceiling_installed_cfg"] = True
        for v in ("gate", "nogate"):
            for c in COLS:
                res["capture"]["%s|%s" % (v, c)] = (float(AL[(v, c)] / AL[("oracle", c)]),) + ci(ALb[(v, c)] / ALb[("oracle", c)])
                LR = A[(v, c)]["LR"].sum(); res["lookup_branch"]["%s|%s" % (v, c)] = dict(
                    share_rounds=float(LR / A[(v, c)]["R"].sum()), mean_tokens_when_lookup=float(A[(v, c)]["LTOK"].sum() / LR) if LR else None)
            for x, yy in (("b", "a"), ("d", "a"), ("c", "a"), ("c", "b"), ("d", "b")):
                res["delta"]["%s|%s_vs_%s" % (v, x, yy)] = (float(AL[(v, x)] / AL[(v, yy)] - 1),) + ci(ALb[(v, x)] / ALb[(v, yy)] - 1)
        for v in ("oracle", "gate", "nogate"):
            a = A[(v, "a")]
            for x in ("b", "d", "c"):
                xx = A[(v, x)]
                pt, pm = rho_star(a["R"].sum(), a["X"].sum(), xx["R"].sum(), xx["X"].sum())
                bt, bm = rho_star(a["R"][S].sum(1), a["X"][S].sum(1), xx["R"][S].sum(1), xx["X"][S].sum(1))
                # closed-form cross-check of the point (linear in rho)
                dR = a["R"].sum() - xx["R"].sum(); dX = xx["X"].sum() - a["X"].sum()
                cf = "mai" if dR <= 0 else (">2" if dX <= 0 or dR / dX > 2 else dR / dX)
                p = fmt_rho(pt[0], pm[0])
                res["rho_star"]["%s|%s_vs_a" % (v, x)] = dict(
                    point=p, closed_form=cf, ci95=[float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))],
                    frac_boot_gt2=float(np.mean(~np.isfinite(bt))), frac_boot_mai=float(np.mean(bm)),
                    s16_over_s1=(1 + 15 * p) if isinstance(p, float) else p, s8_over_s1=(1 + 7 * p) if isinstance(p, float) else p,
                    R_a=float(a["R"].sum()), X_a=float(a["X"].sum()), R_x=float(xx["R"].sum()), X_x=float(xx["X"].sum()))
        OUT["results"][key] = res
        print(key, {"%s|%s" % k: round(v, 4) for k, v in AL.items()}, "mism", mism,
              {k: v["point"] for k, v in res["rho_star"].items()}, flush=True)
json.dump(OUT, open(os.path.join(OUTD, "lookup_rule_al.json"), "w"), indent=1, default=float)
