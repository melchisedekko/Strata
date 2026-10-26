"""POST-HOC, DESCRIPTIVE: STRATA_SPEC_COST=1 vs the default actually deployed (--spec-min-p 0.5, setup.py L9420) on the
ALREADY-USED holdout v1.1 (Strata Lead 04:58 CET).  No decision rule, nothing tuned, frozen params.  tok/s ESTIMATED.
Engine-faithful accounting @7dd5cf18 (charged drafts = drafts the engine launches):
  default_corr : mtp.cpp L1689 drafts while prev prob >= min_p (draft 1 always): n = min(S_mtp-1, 1+run);
                 window generate.cpp L14885-14887: T = min(S_mtp, 1+run); run = leading mtp_p >= 0.5 (proxy-2B traces)
  default_old  : min_p = 0 (CLI default L705): fast path mtp.cpp L1623, n = S_mtp-1 = 3, T = S_mtp = 4
  spec_cost    : chain_rule replaces the min_p test (mtp.cpp L1689 `chain_rule_ ? chain_rule_(j-1,pj) : pj>=min_p`);
                 window T = clamp(chain_rows,1,S_mtp) (L14883-14884); the min_p branch is an `else if` (L14885), so
                 min_p=0.5 changes NOTHING for SPEC_COST (first window: L14889 overrides for every arm; not modelled
                 by the replay for any arm).  = sim2.StrataCurrent(spec_cost=True), kd = chain steps.
  k3           : sim2.MtpFixed(4) reference.
Cells: P1/P2/P4 x rho {0.059..0.1394} band + 0.26 control, V1 and V2 cost files; P4 grid cost_T_d[T,d] control.
sim2.boot_ratio B=2000 seed 0, cluster = session.  usage: script OUTDIR"""
import json, os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strata_sim.sim2 import Profile, load_p4, S_P1, p2_s, boot_ratio, StrataCurrent, MtpFixed, acc_of
from strata_sim.postprocess import load_tf

OUTD = sys.argv[1]; os.makedirs(OUTD, exist_ok=True)
TR = "/workspace/strata-plus/traces/v1.1"
HO = {d: os.path.join(TR, "holdout_%s_tf_d7.jsonl" % d) for d in ("chat", "code", "edit")}
COST = {"V1": "/workspace/strata-plus/traces/cost_p4_cpu.json",
        "V2": os.path.join(HERE, "cost_derived", "cost_p4_cpu_099ceda_s8lin.json")}
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
DOMS = ["code", "chat", "edit"]
R = []
for d in DOMS:
    R += load_tf(HO[d])
REQ = {d: [r for r in R if r["domain"] == d] for d in DOMS}
MIN_P = 0.5
cls = lambda ci: "worse" if ci[2] < 0 else "better" if ci[1] > 0 else "neutral"


class DefaultMinP(StrataCurrent):
    def act(self, q, i, prof):
        p = self.pol
        p.set_context(q["n_prompt"] + i)
        pr = q["mtp_p"][i]; run = 0
        while run < len(pr) and pr[run] >= MIN_P:
            run += 1
        T, kd = min(self.S_mtp, 1 + run), min(self.S_mtp - 1, 1 + run)
        self._T_mtp = T; klu = 0
        if self.lookup:
            kk = int(q[self.srcname + "_k"][i]); klu = kk
            ag = int(q["agree" if self.srcname == "lk" else "agree_pl"][i])
            if kk > 0 and ag >= 1:
                look, t = p.choose(T, min(kk, self.S - 1), int(q[self.srcname + "_m"][i]))
                if look:
                    self._lk = (True, int(q[self.srcname + "_m"][i]))
                    return self.srcname, t, kd, klu
        self._lk = (False, 0)
        return "mtp", T, kd, klu


def walk(policy, reqs, costf):
    """= sim2.walk L81-103 (cost charged with the policy's d = drafts launched)"""
    rows = []
    for q in reqs:
        policy.begin(q)
        n, i = q["n"], 0
        st = dict(N=n, C=0.0, R=0, dm=0, T=0)
        while i < n:
            src, T, d, klu = policy.act(q, i, None)
            T = max(1, min(T, n - i)) if src != "none" else 1
            a = acc_of(q, i, src, T)
            c = costf(T, d, klu)
            st["C"] += c; st["R"] += 1; st["dm"] += d; st["T"] += T
            policy.update(q, i, (src, T, d, klu), a, c)
            i += a + 1
        rows.append(st)
    return rows


RUNS = {"default_old": lambda: StrataCurrent(), "default_corr": lambda: DefaultMinP(),
        "spec_cost": lambda: StrataCurrent(spec_cost=True), "k3": lambda: MtpFixed(4)}
CMP = [("spec_cost", "default_corr"), ("spec_cost", "default_old"), ("spec_cost", "k3"), ("default_corr", "default_old")]


def run_cell(d, costf):
    cl = [q["session"] for q in REQ[d]]
    rows = {n: walk(f(), REQ[d], costf) for n, f in RUNS.items()}
    c = {}
    for a, r in CMP:
        ci = boot_ratio(rows[r], rows[a], cl); c["%s_vs_%s" % (a, r)] = dict(ci=ci, cls=cls(ci))
    c["tps_est"] = {n: float(sum(x["N"] for x in rows[n]) / sum(x["C"] for x in rows[n])) for n in rows}
    c["drafts_per_round"] = {n: float(sum(x["dm"] for x in rows[n]) / sum(x["R"] for x in rows[n])) for n in rows}
    c["T_per_round"] = {n: float(sum(x["T"] for x in rows[n]) / sum(x["R"] for x in rows[n])) for n in rows}
    return c


OUT = {"label": "RIVALUTAZIONE POST-HOC, SOLO DESCRITTIVA, dell'holdout v1.1 gia' usato: SPEC_COST vs default installato "
                "(min_p 0.5). Nessuna regola applicata, nessuna ritaratura. tok/s STIMATI; mtp_p dal proxy llama.cpp 2B.",
       "frozen_params_v3_sha256": sha(os.path.join(HERE, "frozen_params_v3.json")),
       "holdout_files_sha256": {os.path.basename(p): sha(p) for p in HO.values()},
       "script_sha256": sha(os.path.abspath(__file__)), "min_p": MIN_P, "additive": {}, "grid": {}}
for V, cp in COST.items():
    P4 = load_p4(cp); SH = {"P1": S_P1, "P2": p2_s(), "P4": P4.s}
    cells = {}
    for sn, s in SH.items():
        for r in (0.059, 0.0791, 0.0992, 0.1193, 0.1394, 0.26):
            p = Profile("%s|rho%.4f" % (sn, r), s, r, P4.rho_lu, "band" if r < 0.2 else "ctrl")
            for d in DOMS:
                cells["%s|%s" % (d, p.name)] = run_cell(d, p.cost)
    OUT["additive"][V] = dict(cost_path=cp, cost_sha256=sha(cp), cells=cells)
    print(V, "additive done", flush=True)
j = json.load(open(COST["V1"])); ctd = j["cost_T_d"]
gcost = lambda T, d, k: ctd["%d,%d" % (T, min(d, 8))] + j["rho_lu"] * k
OUT["grid"] = {d: run_cell(d, gcost) for d in DOMS}
print("grid done", flush=True)
json.dump(OUT, open(os.path.join(OUTD, "holdout_v11_speccost_vs_default.json"), "w"), indent=0, default=float)
