"""ONE-SHOT holdout v1.1 evaluation with the FROZEN parameters of frozen_params_v3.json (no retuning).
Arms A = GateV2(tmax=5, skip) and B = GateV2(tmax=8, skip) vs default, STRATA_SPEC_COST=1, k=3, plus B vs A; H exploratory
(HybridH min_match=8, lookup min(k,7), tmax=8) reported apart. Per domain x profile (P1/P2/P4 shapes x rho band
0.059..0.1394 + control 0.26) x cost version V1/V2. IC95 = sim2.boot_ratio (cluster bootstrap on session, B=2000), the
frozen method. Rule (frozen): B wins only if in BOTH versions: no B cell worse vs the 3 baselines (band and control) AND
at least one band cell on code or edit with B vs A IC95 > 0; else A. tok/s ESTIMATED (replay, proxy CPU Qwen3.5-2B Q4_K_M).
usage: holdout_v11.py OUTDIR"""
import json, os, sys, collections, datetime, hashlib
import numpy as np
HERE = "/workspace/strata-policy/replay"; sys.path.insert(0, HERE)
from strata_sim.sim2 import Profile, load_p4, S_P1, p2_s, walk, boot_ratio, StrataCurrent, GateV2, MtpFixed, HybridH
from strata_sim.postprocess import load_tf

OUTD = sys.argv[1]; os.makedirs(OUTD, exist_ok=True)
TR = "/workspace/strata-plus/traces/v1.1"
HO = {"tune": "/workspace/strata-plus/traces/v1.1/tf_d7_p30.jsonl"}
COST = {"V1": "/workspace/strata-plus/traces/cost_p4_cpu.json",
        "V2": os.path.join(HERE, "cost_derived", "cost_p4_cpu_099ceda_s8lin.json")}
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
opened = {"opened_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S CET (UTC+1)"),
          "files_sha256_at_open": {os.path.basename(p): sha(p) for p in HO.values()},
          "frozen_params_v3_sha256": sha(os.path.join(HERE, "frozen_params_v3.json")),
          "script": "replay/holdout_v11.py", "script_sha256": sha(os.path.abspath(__file__))}
ap = "/tmp/jg/dry_opened.json"
json.dump(opened, open(ap, "w"), indent=1); os.chmod(ap, 0o444)

DOMS = ["code", "chat", "edit"]
R = []
R = load_tf("/workspace/strata-plus/traces/v1.1/tf_d7_p30.jsonl")
REQ = {d: [r for r in R if r["domain"] == d] for d in DOMS}
POL = {"default": lambda: StrataCurrent(), "spec_cost": lambda: StrataCurrent(spec_cost=True), "k3": lambda: MtpFixed(4),
       "A": lambda: GateV2(tmax=5, skip=True), "B": lambda: GateV2(tmax=8, skip=True),
       "H": lambda: HybridH(min_match=8, factor=None, tmax=8)}
cls = lambda ci: "worse" if ci[2] < 0 else "better" if ci[1] > 0 else "neutral"
OUT = {"data": {"requests": len(R), "per_domain": {d: len(REQ[d]) for d in DOMS}, "rounds": int(sum(r["n"] for r in R)),
                "sessions_per_domain": {d: len({q["session"] for q in REQ[d]}) for d in DOMS},
                "target_mismatch": int(sum(r["target_mismatch"] for r in R))}, "versions": {}}
for V, cp in COST.items():
    P4 = load_p4(cp); SH = {"P1": S_P1, "P2": p2_s(), "P4": P4.s}
    PROFS = [Profile("%s|rho%.4f" % (sn, r), s, r, P4.rho_lu, "band" if r < 0.2 else "ctrl")
             for sn, s in SH.items() for r in (0.059, 0.0791, 0.0992, 0.1193, 0.1394, 0.26)]
    cells, H = {}, collections.Counter()
    for d in DOMS:
        cl = [q["session"] for q in REQ[d]]
        for p in PROFS:
            rows = {n: walk(f(), REQ[d], p) for n, f in POL.items()}
            c = {}
            for arm in ("A", "B", "H"):
                for ref in ("default", "spec_cost", "k3"):
                    ci = boot_ratio(rows[ref], rows[arm], cl); c["%s_vs_%s" % (arm, ref)] = dict(ci=ci, cls=cls(ci))
            for a, b in (("A", "B"), ("A", "H"), ("B", "H")):
                ci = boot_ratio(rows[a], rows[b], cl); c["%s_vs_%s" % (b, a)] = dict(ci=ci, cls=cls(ci))
            c["tps_est"] = {n: float(sum(r["N"] for r in rows[n]) / sum(r["C"] for r in rows[n])) for n in rows}
            cells["%s|%s" % (d, p.name)] = c
    # window histogram of B on band profiles
    for p in PROFS:
        if p.label != "band": continue
        for d in DOMS:
            pol = POL["B"](); orig = pol.act
            def act(q, i, pr, orig=orig):
                r = orig(q, i, pr); T = max(1, min(r[1], q["n"] - i)) if r[0] != "none" else 1; H[T] += 1; return r
            pol.act = act; walk(pol, REQ[d], p)
    tot = sum(H.values())
    band = [k for k in cells if "0.2600" not in k]; ctrl = [k for k in cells if "0.2600" in k]
    worse = {arm: {ref: {"band": [k for k in band if cells[k]["%s_vs_%s" % (arm, ref)]["cls"] == "worse"],
                         "ctrl": [k for k in ctrl if cells[k]["%s_vs_%s" % (arm, ref)]["cls"] == "worse"]}
                   for ref in ("default", "spec_cost", "k3")} for arm in ("A", "B", "H")}
    b_gt_a = [k for k in band if k.split("|")[0] in ("code", "edit") and cells[k]["B_vs_A"]["cls"] == "better"]
    b_no_worse = all(not worse["B"][r][s] for r in worse["B"] for s in ("band", "ctrl"))
    OUT["versions"][V] = dict(cost_path=cp, cost_sha256=sha(cp), s=P4.s, rho_mtp_file=P4.rho_mtp, rho_lu=P4.rho_lu,
                              cells=cells, worse=worse, B_gt_A_code_edit_band=b_gt_a,
                              B_vs_A_band_counts=collections.Counter(cells[k]["B_vs_A"]["cls"] for k in band),
                              B_rounds=dict(total=tot, T8=H[8], share_T8=H[8] / tot, T_ge9=sum(v for t, v in H.items() if t >= 9), maxT=max(H)),
                              rule_B=dict(no_worse_vs_baselines=b_no_worse, beats_A_code_or_edit=len(b_gt_a) > 0,
                                          passes=b_no_worse and len(b_gt_a) > 0))
OUT["verdict"] = "B" if all(OUT["versions"][V]["rule_B"]["passes"] for V in COST) else "A"
OUT["opened"] = opened
json.dump(OUT, open(os.path.join(OUTD, "holdout_v11.json"), "w"), indent=0, default=float)
for V in COST:
    v = OUT["versions"][V]
    print(V, "rule_B", v["rule_B"], "B>A code/edit", len(v["B_gt_A_code_edit_band"]), "B_vs_A band", dict(v["B_vs_A_band_counts"]), "B_rounds", v["B_rounds"])
    for arm in ("A", "B", "H"):
        print("  ", arm, {r: (len(v["worse"][arm][r]["band"]), len(v["worse"][arm][r]["ctrl"])) for r in v["worse"][arm]})
print("VERDICT", OUT["verdict"], OUT["data"])
