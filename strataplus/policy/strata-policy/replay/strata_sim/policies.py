"""Policies for the offline replay. Every policy sees, before acting, only what Strata has at choose() time:
MTP draft probabilities, the lookup proposal (length, match), the agreement length of the two drafts, the position.
After acting it receives the round time of its own action only, plus (full-feedback variants) the counterfactual
acceptance of the other source, CENSORED as online: with a accepted the target emitted a+1 known tokens, so an
alternative draft that matches all of them is only known to reach >= a+1 (failure not observed).
"""
from __future__ import annotations
import math, random
from .draft_policy_port import DraftPolicy, match_bucket, p_bucket

K_MAX = 7


def censored(acc_true: int, k_alt: int, a_chosen: int):
    """What the engine can see online about an alternative draft of length k_alt: (observed accepted, failure seen)."""
    known = a_chosen + 1                    # outv[0..a] are final tokens
    if acc_true < min(k_alt, known):
        return acc_true, True
    return min(acc_true, k_alt, known), False


class Policy:
    name = "?"
    lk_field = "lk"

    def act(self, o):            # -> (src in {"none","mtp","lk"}, k drafts verified, kd MTP drafts computed)
        raise NotImplementedError

    def update(self, o, act, a, T, mtp_acc, lk_acc):
        pass


# ------------------------------------------------------------------------------------------------ (1) current
class Current(Policy):
    """DraftPolicy as wired in the serve loop (generate.cpp:14880-15196): S = 6 window rows (setup --spec 4 ->
    S_mtp = 4, S = min(4+2, 8) at generate.cpp:3205-3211), lookup proposal propose(S-1), gate sbuf[0]==drafts[0].
    spec_cost=True is the STRATA_SPEC_COST=1 arm (keep_draft chain rule + robust costs + observe_probs)."""

    def __init__(self, spec_cost=False, full_feedback=False, gate=True, agree_split=False, frozen=None,
                 lk_field="lk", S=6, S_mtp=4, name=None):
        self.pol = DraftPolicy(S)
        self.pol.robust = spec_cost
        self.spec_cost, self.ff, self.gate, self.agree_split = spec_cost, full_feedback, gate, agree_split
        self.S, self.S_mtp, self.lk_field = S, S_mtp, lk_field
        self.frozen = frozen                       # CostModel -> deterministic mode: costs seeded and never updated
        if frozen is not None:
            self.pol.seed_costs([frozen.mean("mtp", t - 1, S_mtp - 1) for t in range(1, 9)], 8, 1e9)
        self.split = {0: ([0.0] * 4, [0.0] * 4), 1: ([0.0] * 4, [0.0] * 4)}
        self.name = name or ("current" + ("_cost" if spec_cost else "") + ("_ff" if full_feedback else "")
                             + ("" if gate else "_nogate") + ("_agree" if agree_split else "")
                             + ("_frozen" if frozen else "") + ("_pool" if lk_field != "lk" else ""))

    def _swap(self, o):
        if self.agree_split:
            cls = 1 if o[self._ag()] >= 2 else 0
            self.pol.ok, self.pol.bad = self.split[cls]

    def _ag(self):
        return "agree" if self.lk_field == "lk" else "agree_pool"

    def act(self, o):
        p = self.pol
        p.set_context(o["pos"])
        if self.spec_cost:
            T, kd = p.mtp_chain_rows(o["mtp"]["p"], self.S_mtp)
        else:
            T, kd = self.S_mtp, self.S_mtp - 1
        self._T_mtp, self._kd = T, kd
        lk = o[self.lk_field]
        self._lk_k = 0
        if lk is not None and lk["k"] > 0 and (not self.gate or o[self._ag()] >= 1):
            self._lk_k = min(lk["k"], self.S - 1)
            self._swap(o)
            look, t = p.choose(T, self._lk_k, lk["match"])
            if look:
                return "lk", t - 1, kd
        return "mtp", T - 1, kd

    def update(self, o, act, a, T, mtp_acc, lk_acc):
        p = self.pol
        src, k, kd = act
        lk = o[self.lk_field]
        ms = 0.0 if self.frozen is not None else T
        if src == "lk":
            self._swap(o)
            p.observe(True, k + 1, a, lk["match"], ms)
        else:
            p.observe(False, k + 1, a, 0, ms)
            if self.spec_cost:
                p.observe_probs(o["mtp"]["p"], self._T_mtp - 1, a)
        if not self.ff:
            return
        # full feedback (zero-cost counterfactual, censored as the engine would see it)
        if src != "lk" and lk is not None and lk["k"] > 0:
            kf = min(lk["k"], self.S - 1)
            obs, fail = censored(lk_acc, kf, a)
            self._swap(o)
            b = match_bucket(lk["match"])
            p.ok[b] = 0.97 * p.ok[b] + obs
            p.bad[b] = 0.97 * p.bad[b] + (1.0 if fail else 0.0)
        if src == "lk":
            t = self._T_mtp
            obs, fail = censored(mtp_acc, t - 1, a)
            if fail or obs >= t - 1:              # only an uncensored outcome is a valid MTP sample
                got = obs + 1.0
                p.mtp_tok[t] = 0.95 * p.mtp_tok[t] + 0.05 * got if p.mtp_n[t] > 0 else got
                p.mtp_n[t] += 1.0


# ------------------------------------------------------------------------------------------------ shared pieces
class CostEst:
    """Online ridge/RLS fit T ~ th0 + th1*k + th2*kd(+src) from the policy's OWN rounds (costs of actions not taken
    are never observed: they are predicted from the fitted line, never measured counterfactually)."""

    def __init__(self, lam=0.998, src_term=False):
        self.n = 4 if src_term else 3
        self.src_term = src_term
        self.th = [20.0, 6.0, 0.5, 0.0][: self.n]
        self.P = [[(100.0 if i == j else 0.0) for j in range(self.n)] for i in range(self.n)]
        self.lam = lam
        self.seen = False

    def x(self, src, k, kd):
        v = [1.0, float(k), float(kd)]
        if self.src_term:
            v.append(1.0 if src == "mtp" else 0.0)
        return v

    def pred(self, src, k, kd):
        x = self.x(src, k, kd)
        return max(1e-3, sum(a * b for a, b in zip(self.th, x)))

    def update(self, src, k, kd, T):
        if not self.seen:   # anchor intercept at the first measurement so early predictions are in the right units
            self.th[0] = T - self.th[1] * k - self.th[2] * kd
            self.seen = True
        x = self.x(src, k, kd)
        n = self.n
        Px = [sum(self.P[i][j] * x[j] for j in range(n)) for i in range(n)]
        den = self.lam + sum(x[i] * Px[i] for i in range(n))
        g = [v / den for v in Px]
        err = T - sum(a * b for a, b in zip(self.th, x))
        err = max(-3 * self.th[0], min(err, 3 * self.th[0]))          # robust to spikes
        self.th = [self.th[i] + g[i] * err for i in range(n)]
        self.P = [[(self.P[i][j] - g[i] * Px[j]) / self.lam for j in range(n)] for i in range(n)]
        self.th[1] = max(self.th[1], 0.0)
        self.th[2] = max(self.th[2], 0.0)


class Hazard:
    """Decayed Beta counts of 'draft j holds given drafts < j held' per cell."""

    def __init__(self, prior, n0=4.0, decay=0.995):
        self.prior, self.n0, self.decay = prior, n0, decay
        self.ok, self.n = {}, {}

    def rate(self, cell, prior=None):
        pr = self.prior if prior is None else prior
        return (self.ok.get(cell, 0.0) + self.n0 * pr) / (self.n.get(cell, 0.0) + self.n0)

    def add(self, cell, hit):
        self.ok[cell] = self.decay * self.ok.get(cell, 0.0) + (1.0 if hit else 0.0)
        self.n[cell] = self.decay * self.n.get(cell, 0.0) + 1.0


# ------------------------------------------------------------------------------------------------ (3) contextual estimator
class Contextual(Policy):
    """Deterministic, full-feedback, contextual expected-tokens-per-ms policy over {none, MTP@k, lookup@k}.
    Lookup hazard cells: (match bucket, draft index j clipped to 3, inside/outside the MTP-agreement prefix).
    MTP hazard cells: (prob bucket of p_j, inside/outside agreement). Depth k is chosen jointly (adaptive k);
    the MTP chain is drafted sequentially while one more draft can still pay (like keep_draft)."""

    def __init__(self, use_agree=True, mtp_kmax=K_MAX, lk_kmax=K_MAX, lk_field="lk", src_term=False, name=None):
        self.use_agree, self.mtp_kmax, self.lk_kmax, self.lk_field = use_agree, mtp_kmax, lk_kmax, lk_field
        self.hl = Hazard(0.8)
        self.hm = Hazard(0.7)
        self.cost = CostEst(src_term=src_term)
        self.name = name or ("ctx" + ("" if use_agree else "_noagree") + (f"_mtpk{mtp_kmax}" if mtp_kmax != K_MAX else "")
                             + ("_pool" if lk_field != "lk" else ""))

    def _ag(self, o):
        return (o["agree"] if self.lk_field == "lk" else o["agree_pool"]) if self.use_agree else 0

    def _mcell(self, p, j, ag):
        return (p_bucket(p), 1 if j < ag else 0)

    def _lcell(self, match, j, ag):
        return (match_bucket(match), min(j, 3), 1 if j < ag else 0)

    def act(self, o):
        ag = self._ag(o)
        lk = o[self.lk_field]
        ps = o["mtp"]["p"]
        has_lk = lk is not None and lk["k"] > 0
        ag_eff = ag if has_lk else 0
        # sequential MTP chain: draft j is computed only if it can still beat the best so far
        best_v, best = 1.0 / self.cost.pred("none", 0, 0), ("none", 0)
        e, q, kd = 1.0, 1.0, 0
        for j in range(self.mtp_kmax):
            kd = j + 1
            h = self.hm.rate(self._mcell(ps[j], j, ag_eff), prior=ps[j])
            q *= h
            e += q
            v = e / self.cost.pred("mtp", j + 1, kd)
            if v > best_v:
                best_v, best = v, ("mtp", j + 1)
            nxt = (e + q * h) / self.cost.pred("mtp", j + 2, kd + 1)
            if j + 1 >= self.mtp_kmax or nxt <= best_v:
                break
        self._kd = kd
        if has_lk:
            e, q = 1.0, 1.0
            for j in range(min(lk["k"], self.lk_kmax)):
                q *= self.hl.rate(self._lcell(lk["match"], j, ag))
                e += q
                v = e / self.cost.pred("lk", j + 1, kd)
                if v > best_v:
                    best_v, best = v, ("lk", j + 1)
        return best[0], best[1], kd

    def update(self, o, act, a, T, mtp_acc, lk_acc):
        src, k, kd = act
        self.cost.update(src, k, kd, T)
        ag = self._ag(o)
        lk = o[self.lk_field]
        has_lk = lk is not None and lk["k"] > 0
        ag_eff = ag if has_lk else 0
        ps = o["mtp"]["p"]
        # drafts 0..kd-1 exist; what is known about them follows from the a+1 final tokens (censored())
        obs, fail = censored(mtp_acc, kd, a)
        for j in range(min(obs + (1 if fail else 0), kd)):
            self.hm.add(self._mcell(ps[j], j, ag_eff), j < obs)
        if has_lk:
            kl = min(lk["k"], self.lk_kmax)
            obs, fail = censored(lk_acc, kl, a)
            for j in range(min(obs + (1 if fail else 0), kl)):
                self.hl.add(self._lcell(lk["match"], j, ag), j < obs)


# ------------------------------------------------------------------------------------------------ (2) Hedge / full-information
class Hedge(Policy):
    """Full-information exponential weights (HedgeSpec / 'Not-a-Bandit' style) over experts {none, MTP@k, lookup@k}.
    Reward of expert i in a round = tokens_i - lambda * cost_i, lambda = the policy's own running tokens/ms, cost_i
    predicted by CostEst (only the taken action's time is measured). Experts are 'sleeping' when unavailable
    (no lookup proposal / longer than proposal / MTP deeper than drafted). Scores are discounted means per cell;
    contextual=True keys lookup experts by (match bucket, agreement>=1) and MTP/none by p_0 bucket.
    deterministic=True plays the argmax (follow-the-leader); otherwise samples softmax(eta*score), seeded."""

    def __init__(self, contextual=False, deterministic=False, eta=4.0, gamma=0.99, seed=0, mtp_kd=3, lk_field="lk", name=None):
        self.ctx, self.det, self.eta, self.gamma = contextual, deterministic, eta, gamma
        self.rng = random.Random(seed)
        self.S, self.N = {}, {}
        self.cost = CostEst()
        self.kd = mtp_kd
        self.lk_field = lk_field
        self.tok, self.ms = 1.0, 20.0
        self.name = name or ("hedge" + ("_ctx" if contextual else "") + ("_det" if deterministic else "_sto")
                             + ("_pool" if lk_field != "lk" else ""))

    def _key(self, o, e):
        if not self.ctx:
            return e
        lk = o[self.lk_field]
        if e[0] == "lk":
            ag = o["agree"] if self.lk_field == "lk" else o["agree_pool"]
            return e + (match_bucket(lk["match"]), 1 if ag >= 1 else 0)
        return e + (min(int(o["mtp"]["p"][0] * 4), 3),)

    def experts(self, o):
        ex = [("none", 0)] + [("mtp", k) for k in range(1, self.kd + 1)]
        lk = o[self.lk_field]
        if lk is not None:
            ex += [("lk", k) for k in range(1, min(lk["k"], K_MAX) + 1)]
        return ex

    def score(self, key):
        n = self.N.get(key, 0.0)
        return self.S.get(key, 0.0) / n if n > 0 else 1e9    # optimistic: unseen expert is tried

    def act(self, o):
        ex = self.experts(o)
        sc = [self.score(self._key(o, e)) for e in ex]
        if self.det or max(sc) >= 1e9:
            i = max(range(len(ex)), key=lambda i: sc[i])
        else:
            m = max(sc)
            w = [math.exp(self.eta * (s - m)) for s in sc]
            x = self.rng.random() * sum(w)
            i = 0
            while x > w[i]:
                x -= w[i]
                i += 1
        return ex[i][0], ex[i][1], self.kd

    def update(self, o, act, a, T, mtp_acc, lk_acc):
        src, k, kd = act
        self.cost.update(src, k, kd, T)
        self.tok = 0.995 * self.tok + (a + 1)
        self.ms = 0.995 * self.ms + T
        lam = self.tok / self.ms
        mo, mf = censored(mtp_acc, kd, a)
        lk = o[self.lk_field]
        if lk is not None:
            lo, lf = censored(lk_acc, min(lk["k"], K_MAX), a)
        for e in self.experts(o):
            s, kk = e
            if s == "none":
                tok = 1
            else:
                obs, fail = (mo, mf) if s == "mtp" else (lo, lf)
                if not fail and kk > obs:
                    continue          # this expert's outcome is censored: no feedback
                tok = min(obs, kk) + 1
            r = tok - lam * self.cost.pred(s, kk, kd)
            key = self._key(o, e)
            self.S[key] = self.gamma * self.S.get(key, 0.0) + r
            self.N[key] = self.gamma * self.N.get(key, 0.0) + 1.0
