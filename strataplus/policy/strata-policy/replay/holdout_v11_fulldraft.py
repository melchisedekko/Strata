"""POST-HOC REASSESSMENT of the already-used holdout v1.1 (NOT a new validation): corrects the cost model to what the
engine pays with the P6 hook.  The upstream engine drafts S_mtp-1 MTP tokens at the end of EVERY round
(mtp.cpp max_steps = min(max_t-1, max_drafts), generate.cpp set_max_drafts(S_mtp-1)), also when the next round is a
lookup or a skip; only STRATA_SPEC_COST=1 shortens the chain (chain rule).  The replay (sim2.walk -> Profile.cost(T, d, klu))
charges rho_mtp*d with the d the POLICY chose: right for the baselines (default d=S_mtp-1=3 every round, k=3 d=3,
spec_cost d=chain steps), optimistic for the gate arms (skip -> d=0, shallow d).  Here: A drafts d_full=4 (needs S_mtp=5)
and B d_full=7 (S_mtp=8) EVERY round; the gate observes that cost (as P6's observe of the measured round ms).
Frozen parameters (frozen_params_v3.json), same cells, same bootstrap (sim2.boot_ratio, B=2000, seed 0).  DESCRIPTIVE ONLY:
no decision rule applied, A vs B choice unchanged (Strata Lead).  Primary: rho band 0.059-0.1394; 0.26 control only.
Also: P4 grid table (cost_T_d of cost_p4_cpu.json, d=0..8), before = d chosen, after = d the engine drafts.
tok/s ESTIMATED (replay, proxy CPU Qwen3.5-2B Q4_K_M).  usage: holdout_v11_fulldraft.py OUTDIR"""
import json, os, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strata_sim.sim2 import Profile, load_p4, S_P1, p2_s, walk, boot_ratio, StrataCurrent, GateV2, MtpFixed
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
D_FULL = {"default": None, "spec_cost": None, "k3": None, "A": 4, "B": 7}   # None: the replay's d is already the engine's
POL = {"default": lambda: StrataCurrent(), "spec_cost": lambda: StrataCurrent(spec_cost=True), "k3": lambda: MtpFixed(4),
       "A": lambda: GateV2(tmax=5, skip=True), "B": lambda: GateV2(tmax=8, skip=True)}
cls = lambda ci: "worse" if ci[2] < 0 else "better" if ci[1] > 0 else "neutral"


class FullDraft(Profile):
    """additive model, the draft term charged at the engine's depth every round"""
    def __init__(self, p, d_full):
        super().__init__(p.name, p.s, p.rho_mtp, p.rho_lu, p.label); self.d_full = d_full
    def cost(self, T, d_mtp, k_lu):
        return super().cost(T, self.d_full, k_lu)


class Grid(Profile):
    """P4 measured grid cost_T_d[T,d] (+ rho_lu*klu as the file's cost_def); d_full=None: the policy's d"""
    def __init__(self, ctd, rho_lu, d_full):
        super().__init__("P4grid", [ctd["%d,0" % t] for t in range(1, 9)], 0.0, rho_lu, "cost_T_d"); self.g, self.d_full = ctd, d_full
    def cost(self, T, d_mtp, k_lu):
        d = d_mtp if self.d_full is None else self.d_full
        return self.g["%d,%d" % (T, min(d, 8))] + self.rho_lu * k_lu


def cells_for(prof_before, prof_after_of):
    """rows before/after for every policy; returns the comparison dict"""
    out = {}
    for d in DOMS:
        cl = [q["session"] for q in REQ[d]]
        rows = {}
        for n, f in POL.items():
            rows[n] = walk(f(), REQ[d], prof_after_of(n))
        c = {}
        for arm in ("A", "B"):
            for ref in ("default", "spec_cost", "k3"):
                ci = boot_ratio(rows[ref], rows[arm], cl); c["%s_vs_%s" % (arm, ref)] = dict(ci=ci, cls=cls(ci))
        c["tps_est"] = {n: float(sum(r["N"] for r in rows[n]) / sum(r["C"] for r in rows[n])) for n in rows}
        c["dm_per_round"] = {n: float(sum(r["dm"] for r in rows[n]) / sum(r["R"] for r in rows[n])) for n in rows}
        out[d] = c
    return out


OUT = {"label": "RIVALUTAZIONE POST-HOC dell'holdout v1.1 gia' usato (correzione del modello di costo: draft MTP pieno "
                "a ogni round come nel motore con P6). NON e' una nuova validazione; solo descrittiva, nessuna regola applicata.",
       "frozen_params_v3_sha256": sha(os.path.join(HERE, "frozen_params_v3.json")),
       "holdout_files_sha256": {os.path.basename(p): sha(p) for p in HO.values()},
       "script_sha256": sha(os.path.abspath(__file__)), "d_full": D_FULL, "additive": {}, "grid": {}}
for V, cp in COST.items():
    P4 = load_p4(cp); SH = {"P1": S_P1, "P2": p2_s(), "P4": P4.s}
    cells = {}
    for sn, s in SH.items():
        for r in (0.059, 0.0791, 0.0992, 0.1193, 0.1394, 0.26):
            p = Profile("%s|rho%.4f" % (sn, r), s, r, P4.rho_lu, "band" if r < 0.2 else "ctrl")
            res = cells_for(p, lambda n, p=p: p if D_FULL[n] is None else FullDraft(p, D_FULL[n]))
            for d, c in res.items():
                cells["%s|%s" % (d, p.name)] = c
    OUT["additive"][V] = dict(cost_path=cp, cost_sha256=sha(cp), cells=cells)
    print(V, "additive done", flush=True)
# P4 measured grid (cost_T_d identical in V1 and V2: only s(8) differs, not used here)
j = json.load(open(COST["V1"])); ctd = j["cost_T_d"]
for when in ("before", "after"):
    res = cells_for(None, lambda n, when=when: Grid(ctd, j["rho_lu"], None if (when == "before" or D_FULL[n] is None) else D_FULL[n]))
    OUT["grid"][when] = res
print("grid done", flush=True)
json.dump(OUT, open(os.path.join(OUTD, "holdout_v11_fulldraft.json"), "w"), indent=0, default=float)
