"""Faithful Python port of strata::spec::DraftPolicy (include/strata/spec/draft_policy.hpp,
src/spec/draft_policy.cpp) at Strata commit 7dd5cf18e68c639a8773e096c5c79f971ea2a9f5.

Every constant and branch mirrors the C++; crosscheck/ verifies picks against the compiled C++ on
random operation streams. Do not "improve" this file: it is the baseline (policy (1) of the replay).
"""
from __future__ import annotations

K_MAX_T = 8
K_BUCKETS = 4
K_CTX_BUCKETS = 3
K_SHAPE = [0.0, 1.0, 1.35, 1.7, 2.05, 2.45, 2.85, 3.25, 3.6]
K_COST_ALPHA = 0.1
K_TOK_ALPHA = 0.05
K_CAL_DECAY = 0.995
K_DECAY = 0.97
K_PRIOR_Q = [0.75, 0.88, 0.93, 0.96]
K_PRIOR_N = 4.0
K_PROBES = 3
K_STALE_ROUNDS = 300.0
K_PBUCKETS = 8
K_CHAIN_PRIOR = [0.45, 0.65, 0.8, 0.9]


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def match_bucket(match: int) -> int:
    return 0 if match < 6 else 1 if match < 12 else 2 if match < 24 else 3


def p_bucket(p: float) -> int:
    b = int(p * 8.0)
    return 0 if b < 0 else 7 if b > 7 else b


class ChainState:
    __slots__ = ("q", "e", "best_v", "best_rows", "kept")

    def __init__(self):
        self.q = 1.0
        self.e = 1.0
        self.best_v = 0.0
        self.best_rows = 1
        self.kept = 0


class DraftPolicy:
    def __init__(self, max_t: int, margin: float = 0.03):
        self.max_t = _clamp(max_t, 1, K_MAX_T)
        self.margin = margin
        self.cost = [[0.0] * (K_MAX_T + 1) for _ in range(K_CTX_BUCKETS)]
        self.cost_n = [[0.0] * (K_MAX_T + 1) for _ in range(K_CTX_BUCKETS)]
        self.last = [[0.0] * (K_MAX_T + 1) for _ in range(K_CTX_BUCKETS)]
        self.bk = 0
        self.mtp_tok = [0.0] * (K_MAX_T + 1)
        self.mtp_n = [0.0] * (K_MAX_T + 1)
        self.ok = [0.0] * K_BUCKETS
        self.bad = [0.0] * K_BUCKETS
        self.cok = [0.0] * K_BUCKETS
        self.cbad = [0.0] * K_BUCKETS
        self.rounds = 0.0
        self.robust = False
        self.pa_ok = [0.0] * K_PBUCKETS
        self.pa_n = [0.0] * K_PBUCKETS

    # --- estimates -------------------------------------------------------------------------
    def lookup_rate(self, match: int) -> float:
        b = match_bucket(match)
        return (self.ok[b] + K_PRIOR_N * K_PRIOR_Q[b]) / (self.ok[b] + self.bad[b] + K_PRIOR_N)

    def cost_ms(self, t: int) -> float:
        t = _clamp(t, 1, K_MAX_T)
        cn, c = self.cost_n[self.bk], self.cost[self.bk]
        if cn[t] > 0:
            return c[t]
        num = den = 0.0
        for u in range(1, K_MAX_T + 1):
            if cn[u] > 0:
                w = min(cn[u], 20.0)
                num += w * c[u] * K_SHAPE[t] / K_SHAPE[u]
                den += w
        return num / den if den > 0 else K_SHAPE[t]

    def clamp_sample(self, t: int, ms: float) -> float:
        if not self.robust:
            return ms
        known = self.cost_ms(t)
        if self.cost_n[self.bk][t] == 0:
            for u in range(1, K_MAX_T + 1):
                if self.cost_n[self.bk][u] > 0:
                    return known
            return ms
        return min(ms, 2.0 * known)

    def seed_costs(self, ms, n, weight, bucket=0):
        bucket = _clamp(bucket, 0, K_CTX_BUCKETS - 1)
        for t in range(1, min(n, K_MAX_T) + 1):
            if ms[t - 1] > 0.0 and self.cost_n[bucket][t] == 0:
                self.cost[bucket][t] = ms[t - 1]
                self.cost_n[bucket][t] = weight

    def set_context(self, pos: int):
        if not self.robust:
            return
        nb = 0 if pos < 6000 else 1 if pos < 24000 else 2
        if nb == self.bk:
            return
        has = any(self.cost_n[nb][t] > 0 for t in range(1, K_MAX_T + 1))
        if not has:
            for d in range(1, K_CTX_BUCKETS):
                if has:
                    break
                for src in (nb - d, nb + d):
                    if src < 0 or src >= K_CTX_BUCKETS or has:
                        continue
                    for t in range(1, K_MAX_T + 1):
                        if self.cost_n[src][t] > 0:
                            self.cost[nb][t] = self.cost[src][t]
                            self.cost_n[nb][t] = 1.0
                            self.last[nb][t] = self.rounds
                            has = True
        self.bk = nb

    def stale(self, t: int) -> bool:
        return self.cost_n[self.bk][t] > 0 and self.rounds - self.last[self.bk][t] > K_STALE_ROUNDS

    def mtp_tokens(self, t: int) -> float:
        if self.mtp_n[t] > 0:
            return self.mtp_tok[t]
        return 1.0 + 0.7 * (t - 1)

    # --- choose / observe --------------------------------------------------------------------
    def choose(self, t_mtp: int, lookup_k: int, match: int):
        """Returns (lookup: bool, t: int)."""
        pt = _clamp(t_mtp, 1, self.max_t)
        if lookup_k <= 0:
            return False, pt
        base = self.mtp_tokens(pt) / self.cost_ms(pt)
        q = self.lookup_rate(match)
        e = 1.0
        qi = 1.0
        best = 0.0
        best_t = 0
        kmax = min(lookup_k, self.max_t - 1)
        for k in range(1, kmax + 1):
            qi *= q
            e += qi
            r = e / self.cost_ms(k + 1)
            if r > best:
                best = r
                best_t = k + 1
        t_full = kmax + 1
        if best_t > 0 and best > base * (1.0 + self.margin):
            t = best_t
            if best_t < t_full and q >= 0.85 and self.stale(t_full):
                t = t_full
            return True, t
        if t_full > pt and (self.cost_n[self.bk][t_full] < K_PROBES or self.stale(t_full)) and q >= 0.85:
            return True, t_full
        return False, pt

    def _cost_sample(self, t, round_ms):
        round_ms = self.clamp_sample(t, round_ms)
        cn = self.cost_n[self.bk]
        alpha = max(K_COST_ALPHA, 1.0 / (cn[t] + 1.0)) if self.robust else K_COST_ALPHA
        c = self.cost[self.bk]
        c[t] = (1.0 - alpha) * c[t] + alpha * round_ms if cn[t] > 0 else round_ms
        cn[t] += 1.0
        self.last[self.bk][t] = self.rounds

    def observe(self, lookup: bool, t: int, accepted: int, match: int, round_ms: float):
        t = _clamp(t, 1, K_MAX_T)
        if round_ms > 0:
            self._cost_sample(t, round_ms)
        self.rounds += 1.0
        if lookup:
            b = match_bucket(match)
            self.ok[b] = K_DECAY * self.ok[b] + accepted
            self.bad[b] = K_DECAY * self.bad[b] + (1.0 if accepted < t - 1 else 0.0)
        else:
            got = accepted + 1.0
            self.mtp_tok[t] = (1.0 - K_TOK_ALPHA) * self.mtp_tok[t] + K_TOK_ALPHA * got if self.mtp_n[t] > 0 else got
            self.mtp_n[t] += 1.0

    # --- STRATA_SPEC_COST: cost-aware MTP window ---------------------------------------------
    def draft_rate(self, p: float) -> float:
        b = p_bucket(p)
        centre = _clamp(p, 0.0, 1.0)
        return (self.pa_ok[b] + K_PRIOR_N * centre) / (self.pa_n[b] + K_PRIOR_N)

    def observe_probs(self, p, n, accepted):
        for j in range(n):
            if j > accepted:
                break
            b = p_bucket(p[j])
            self.pa_ok[b] = K_CAL_DECAY * self.pa_ok[b] + (1.0 if j < accepted else 0.0)
            self.pa_n[b] = K_CAL_DECAY * self.pa_n[b] + 1.0

    def keep_draft(self, st: ChainState, idx: int, p: float, cap: int) -> bool:
        cap = _clamp(cap, 1, self.max_t)
        if idx == 0:
            st.__init__()
            st.best_v = 1.0 / self.cost_ms(1)
        a = self.draft_rate(p)
        st.q *= a
        st.e += st.q
        rows = idx + 2
        m3 = self.margin / 3.0
        if rows <= cap:
            v = st.e / self.cost_ms(rows)
            if v > st.best_v * (1.0 + m3):
                st.best_v = v
                st.best_rows = rows
            if self.cost_n[self.bk][rows] < K_PROBES and st.q >= 0.15:
                st.best_rows = rows
        st.kept = st.best_rows - 1
        if rows + 1 > cap:
            return False
        v1 = (st.e + st.q * a) / self.cost_ms(rows + 1)
        v2 = (st.e + st.q * a + st.q * a * a) / self.cost_ms(rows + 2) if rows + 2 <= cap else 0.0
        return max(v1, v2) > st.best_v * (1.0 + m3) or (self.cost_n[self.bk][rows + 1] < K_PROBES and st.q * a >= 0.15)

    def mtp_chain_rows(self, probs, cap: int):
        """Mirror of MtpDrafter::draft with the STRATA_SPEC_COST chain rule (src/core/mtp.cpp:1689-1708):
        draft j+1 is computed only if keep_draft(j, p_j) holds; returns (window rows kept, drafts computed)."""
        st = ChainState()
        max_steps = cap - 1
        n = 0
        for idx in range(max_steps):
            n = idx + 1
            if not self.keep_draft(st, idx, probs[idx], cap):
                break
        return st.best_rows, max(n, 1)
