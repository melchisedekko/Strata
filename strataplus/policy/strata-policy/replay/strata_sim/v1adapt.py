"""Adapter: runs the v1 policy family (strata_sim/policies.py: Hedge full-feedback, contextual estimator,
agreement split/bonus, deterministic follow-the-leader, current+full-feedback) inside the v2 walk (sim2.walk), so they
are scored on the same data, cost profiles, oracles and bootstrap as the v2 candidates.
Mapping: v1 act -> (src, k drafts verified, kd MTP drafts computed)  =>  v2 (src, T=k+1, d=kd, klu=lookup k probed).
v1 update expects ms (CostEst prior th=[20,6,0.5] ms): the v2 step-unit cost c is passed as c*MS_PER_STEP (=20 ms,
the v1 prior intercept), so the v1 priors keep their intended scale."""
from __future__ import annotations
from . import policies as P1

MS_PER_STEP = 20.0


class V1(object):
    def __init__(self, pol, name=None, pool=False):
        self.p, self.pool = pol, pool
        self.name = name or pol.name

    def begin(self, q):
        if hasattr(self.p, "begin"):
            self.p.begin(q)

    def _obs(self, q, i):
        def lk(kk, mm):
            k = int(q[kk][i]) if kk in q else 0
            return {"k": k, "match": int(q[mm][i])} if k > 0 else None
        o = {"pos": i, "mtp": {"k": len(q["mtp_p"][i]), "p": [float(x) for x in q["mtp_p"][i]], "acc": int(q["mtp_acc"][i])},
             "lk": lk("lk_k", "lk_m"), "agree": int(q["agree"][i]),
             "lk_pool": lk("pl_k", "pl_m") if "pl_k" in q else None,
             "agree_pool": int(q["agree_pl"][i]) if "agree_pl" in q else 0}
        if self.pool and o["lk_pool"] is None:          # pool falls back to the request's own lookup
            o["lk_pool"], o["agree_pool"] = o["lk"], o["agree"]
        return o

    def act(self, q, i, prof):
        o = self._obs(q, i)
        src, k, kd = self.p.act(o)
        self._o, self._a1 = o, (src, k, kd)
        lk = o[self.p.lk_field]
        klu = lk["k"] if lk is not None else 0
        src2 = "pl" if (src == "lk" and self.p.lk_field != "lk") else src
        if src == "none":
            return "none", 1, kd, klu
        return src2, k + 1, kd, klu

    def update(self, q, i, act, a, c):
        src = self._a1[0]
        lk_acc = int(q["pl_acc" if self.p.lk_field != "lk" else "lk_acc"][i])
        self.p.update(self._o, self._a1, a, c * MS_PER_STEP, int(q["mtp_acc"][i]), lk_acc)


def variants():
    return [V1(P1.Current(full_feedback=True), "v1_current_ff"),
            V1(P1.Current(agree_split=True), "v1_current_agree"),
            V1(P1.Current(gate=False), "v1_current_nogate"),
            V1(P1.Contextual(), "v1_ctx_agree"),
            V1(P1.Contextual(use_agree=False), "v1_ctx_noagree"),
            V1(P1.Hedge(), "v1_hedge_sto"),
            V1(P1.Hedge(deterministic=True), "v1_hedge_det"),
            V1(P1.Hedge(contextual=True, deterministic=True), "v1_hedge_ctx_det"),
            V1(P1.Hedge(contextual=True), "v1_hedge_ctx_sto")]
