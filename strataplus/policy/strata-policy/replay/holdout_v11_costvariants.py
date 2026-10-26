"""POST-HOC, DESCRIPTIVE reassessment of arm A (GateV2 tmax=5, skip) on the ALREADY-USED holdout v1.1 under four draft
cost accountings (Strata Lead 04:53 CET).  NOT a new validation; no decision rule; A vs B not reopened; nothing tuned.
  ORIG   : the replay's cost (draft charged = the gate's d; skip/lookup-first -> 0)
  M-full : the engine drafts the whole chain every round (S_mtp=5 -> 4 drafts)
  M-real : max(d,1) drafts (round graph + drafts[0] always paid; skip/lookup-first -> 1); = a chain_rule-style cut
  M-cap  : the cap is fixed at the end of round r BEFORE drafting; the round pays the cap (skip -> 1); the usable depth is
           min(d_gate, cap).  cap rule 'prev' (no new parameter): first round cap = tmax-1; next cap = max(1, w) where w is
           the depth at which the frozen value test stops when run on the drafts actually seen (<= cap) and, beyond the cap,
           on the gate's own hazard extrapolation (sim2 GateV2._mtp_haz L420-424).  cap rule 'tmax-1' == M-full (identical).
Baselines: default OLD (replay: S_mtp=4, 3 drafts every round, window 4 = engine with --spec-min-p 0),
default CORR (--spec-min-p 0.5 as setup.py writes: chain cut mtp.cpp L1689, window generate.cpp L14885-14887),
STRATA_SPEC_COST=1 (chain rule, unchanged), k=3 (unchanged).  Frozen params, same cells, sim2.boot_ratio B=2000 seed 0.
P4 control: measured grid cost_T_d[T, d_charged] (d=max(d,1) for M-real).  tok/s ESTIMATED.  usage: script OUTDIR"""
import json, os, sys, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strata_sim.sim2 import (Profile, load_p4, S_P1, p2_s, boot_ratio, StrataCurrent, GateV2, MtpFixed, acc_of, DMAX)
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
    """serve loop with --spec-min-p 0.5 and STRATA_SPEC_COST unset: mtp.cpp L1686-1700 drafts while the previous draft's
    prob >= min_p (draft 1 always) -> n = min(S_mtp-1, 1+run); window generate.cpp L14885-14887 T = min(S_mtp, 1+run)"""
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


class GateCap(GateV2):
    """GateV2.act (sim2.py L457-501) with a cap fixed before drafting (rule 'prev'); frozen parameters untouched"""
    def begin(self, q):
        super().begin(q); self.cap = self.tmax - 1; self.w_log = []

    def act(self, q, i, prof):
        lam = self.lam(); rem = q["n"] - i - 1
        klu = self._klu(q, i)
        v0 = 1.0 - lam * self.cost.pred(1, 0, klu)
        bl = self._best_lookup(q, i, 0, False, lam, rem) if self.srcs else None
        if not self.mtp or rem <= 0:
            self._charge = 1
            if bl and bl[0] > v0:
                return bl[1], bl[2], 0, klu
            return "none", 1, 0, klu
        hm = self._mtp_haz([])
        Em = self._expect(hm, min(self.tmax - 1, rem))
        vm_prior = max(Em[k] - lam * self.cost.pred(k + 1, k, klu) for k in range(1, len(Em)))
        if self.skip and bl and bl[0] >= vm_prior and bl[0] > v0:   # decidable before drafting (no draft feature used)
            self._charge = 1
            return bl[1], bl[2], 0, klu
        kmax = min(DMAX, self.tmax - 1, rem); kcap = max(1, min(kmax, self.cap))
        self._charge = kcap
        probs, d = [], 0
        while d < kmax:                              # same value test; beyond the cap no real prob is appended
            if d < kcap:
                probs.append(float(q["mtp_p"][i][d]))
            d += 1
            if d >= kmax:
                break
            h = self._mtp_haz(probs)
            E = self._expect(h, kmax)
            now = max(E[k] - lam * self.cost.pred(k + 1, d, klu) for k in range(0, d + 1))
            ahead = max(E[k] - lam * self.cost.pred(k + 1, k, klu) for k in range(d + 1, kmax + 1))
            if ahead <= now:
                break
        w = d; d = min(w, kcap); probs = probs[:d]
        self.cap = max(1, w); self.w_log.append(w)
        h = self._mtp_haz(probs)
        E = self._expect(h, d)
        cand = [("mtp", k + 1, E[k] - lam * self.cost.pred(k + 1, d, klu)) for k in range(1, d + 1)]
        cand.append(("none", 1, 1.0 - lam * self.cost.pred(1, d, klu)))
        bl = self._best_lookup(q, i, d, True, lam, rem) if self.srcs else None
        if bl:
            cand.append((bl[1], bl[2], bl[0]))
        s, T, _ = max(cand, key=lambda x: x[2])
        self._probs = probs
        return s, T, d, klu


def walk2(policy, reqs, costf, charge):
    """sim2.walk (L81-103) with the drafted depth charged separately: charge(policy, d) -> drafts paid this round"""
    rows = []
    for q in reqs:
        policy.begin(q)
        n, i = q["n"], 0
        st = dict(N=n, C=0.0, R=0, dm=0, dc=0)
        while i < n:
            policy._charge = None
            src, T, d, klu = policy.act(q, i, None)
            T = max(1, min(T, n - i)) if src != "none" else 1
            a = acc_of(q, i, src, T)
            dc = charge(policy, d)
            c = costf(T, dc, klu)
            st["C"] += c; st["R"] += 1; st["dm"] += d; st["dc"] += dc
            policy.update(q, i, (src, T, d, klu), a, c)
            i += a + 1
        rows.append(st)
    return rows


CH = {"same": lambda p, d: d, "full": lambda p, d: 4, "real": lambda p, d: max(d, 1), "cap": lambda p, d: p._charge}
RUNS = {"default_old": (lambda: StrataCurrent(), "same"), "default_corr": (lambda: DefaultMinP(), "same"),
        "spec_cost": (lambda: StrataCurrent(spec_cost=True), "same"), "k3": (lambda: MtpFixed(4), "same"),
        "A_ORIG": (lambda: GateV2(tmax=5, skip=True), "same"), "A_Mfull": (lambda: GateV2(tmax=5, skip=True), "full"),
        "A_Mreal": (lambda: GateV2(tmax=5, skip=True), "real"), "A_Mcap": (lambda: GateCap(tmax=5, skip=True), "cap")}
ARMS = ["A_ORIG", "A_Mfull", "A_Mreal", "A_Mcap"]; REFS = ["default_old", "default_corr", "spec_cost", "k3"]


def run_cell(d, costf):
    cl = [q["session"] for q in REQ[d]]
    rows = {n: walk2(f(), REQ[d], costf, CH[m]) for n, (f, m) in RUNS.items()}
    c = {}
    for arm in ARMS:
        for ref in REFS:
            ci = boot_ratio(rows[ref], rows[arm], cl); c["%s_vs_%s" % (arm, ref)] = dict(ci=ci, cls=cls(ci))
    c["tps_est"] = {n: float(sum(r["N"] for r in rows[n]) / sum(r["C"] for r in rows[n])) for n in rows}
    c["d_gate_per_round"] = {n: float(sum(r["dm"] for r in rows[n]) / sum(r["R"] for r in rows[n])) for n in rows}
    c["d_charged_per_round"] = {n: float(sum(r["dc"] for r in rows[n]) / sum(r["R"] for r in rows[n])) for n in rows}
    return c


OUT = {"label": "RIVALUTAZIONE POST-HOC, SOLO DESCRITTIVA, dell'holdout v1.1 gia' usato: varianti di costo del draft per A. "
                "Non e' una nuova validazione; nessuna regola applicata; A/B non riaperto; nessuna ritaratura.",
       "frozen_params_v3_sha256": sha(os.path.join(HERE, "frozen_params_v3.json")),
       "holdout_files_sha256": {os.path.basename(p): sha(p) for p in HO.values()},
       "script_sha256": sha(os.path.abspath(__file__)), "min_p_default_corr": MIN_P, "additive": {}, "grid": {}}
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
json.dump(OUT, open(os.path.join(OUTD, "holdout_v11_costvariants.json"), "w"), indent=0, default=float)
