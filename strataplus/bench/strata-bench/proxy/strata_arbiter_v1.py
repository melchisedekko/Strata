"""strata_arbiter_v1.py - strata-plus, PROXY CPU, non AMD. Port Python riga per riga di proxy/strata_arbiter_v1.hpp
(copia fedele di DraftPolicy::choose/observe + gate generate.cpp L16536-16568 di Strata @7dd5cf1, MIT; s(T) FISSO, niente EMA).
Il file C++ e' il riferimento; questo port serve al replay (Policy) e al controllo di coerenza: nessuna logica in piu'.
Aritmetica in double come il C++; il confronto p >= spec_min_p usa float32 come il C++ ((float) spec_min_p)."""
import struct
K_MAXT = 8
K_SHAPE = (0.0, 1.0, 1.35, 1.7, 2.05, 2.45, 2.85, 3.25, 3.6)
K_TOK_ALPHA = 0.05; K_DECAY = 0.97; K_PRIOR_Q = (0.75, 0.88, 0.93, 0.96); K_PRIOR_N = 4.0
K_PROBES = 3; K_STALE_ROUNDS = 300.0; K_MARGIN = 0.03
def _f32(x): return struct.unpack('f', struct.pack('f', x))[0]
def _clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v
class Arbiter:
    def __init__(self, max_t, s=K_SHAPE, margin=K_MARGIN):
        self.max_t = _clamp(max_t, 1, K_MAXT); self.margin = margin; self.s = tuple(s)
        self.cost_n = [0.0] * (K_MAXT + 1); self.last = [0.0] * (K_MAXT + 1)
        self.mtp_tok = [0.0] * (K_MAXT + 1); self.mtp_n = [0.0] * (K_MAXT + 1)
        self.ok = [0.0] * 4; self.bad = [0.0] * 4; self.rounds = 0.0
    @staticmethod
    def bucket(m): return 0 if m < 6 else 1 if m < 12 else 2 if m < 24 else 3
    def lookup_rate(self, m):
        b = self.bucket(m); return (self.ok[b] + K_PRIOR_N * K_PRIOR_Q[b]) / (self.ok[b] + self.bad[b] + K_PRIOR_N)
    def cost_ms(self, t): return self.s[_clamp(t, 1, K_MAXT)]
    def stale(self, t): return self.cost_n[t] > 0 and self.rounds - self.last[t] > K_STALE_ROUNDS
    def mtp_tokens(self, t): return self.mtp_tok[t] if self.mtp_n[t] > 0 else 1.0 + 0.7 * (t - 1)
    def choose(self, t_mtp, lookup_k, match):
        t = _clamp(t_mtp, 1, self.max_t)
        if lookup_k <= 0: return False, t
        base = self.mtp_tokens(t) / self.cost_ms(t); q = self.lookup_rate(match)
        e = 1.0; qi = 1.0; best = 0.0; best_t = 0
        for k in range(1, min(lookup_k, self.max_t - 1) + 1):
            qi *= q; e += qi; r = e / self.cost_ms(k + 1)
            if r > best: best = r; best_t = k + 1
        t_full = min(lookup_k, self.max_t - 1) + 1
        if best_t > 0 and best > base * (1.0 + self.margin):
            tt = best_t
            if best_t < t_full and q >= 0.85 and self.stale(t_full): tt = t_full
            return True, tt
        if t_full > t and (self.cost_n[t_full] < K_PROBES or self.stale(t_full)) and q >= 0.85: return True, t_full
        return False, t
    def observe(self, lookup, t, accepted, match):
        t = _clamp(t, 1, K_MAXT)
        self.cost_n[t] += 1.0; self.last[t] = self.rounds; self.rounds += 1.0
        if lookup:
            b = self.bucket(match)
            self.ok[b] = K_DECAY * self.ok[b] + accepted
            self.bad[b] = K_DECAY * self.bad[b] + (1.0 if accepted < t - 1 else 0.0)
        else:
            got = accepted + 1.0
            self.mtp_tok[t] = (1.0 - K_TOK_ALPHA) * self.mtp_tok[t] + K_TOK_ALPHA * got if self.mtp_n[t] > 0 else got
            self.mtp_n[t] += 1.0
def decide(a, S, S_mtp, spec_min_p, mtp_p, k, match, sbuf0, draft0, room):
    """-> dict(T, lookup, gate, choose_called, T_pre_room, t_mtp). mtp_p: lista probabilita' dei draft MTP (len = n_mtp)."""
    T = S_mtp
    if spec_min_p > 0.0:
        T = 1; thr = _f32(spec_min_p)
        while T < S_mtp and T - 1 < len(mtp_p) and _f32(mtp_p[T - 1]) >= thr: T += 1
    d = {'t_mtp': T, 'gate': False, 'choose_called': False, 'lookup': False}
    if k > 0 and len(mtp_p) > 0 and sbuf0 == draft0:
        d['gate'] = d['choose_called'] = True
        lk, t = a.choose(T, k, match)
        if lk: T = t; d['lookup'] = True
    d['T_pre_room'] = T; d['T'] = min(T, max(room, 1))
    return d
