"""SYNTHETIC per-round trace generator (NOT measured data).

Produces records in the replay format of /workspace/strata-plus/log_format.md (section "Replay record"),
with "synthetic": true on every line. All regime parameters below are ASSUMPTIONS chosen to exercise the
policies (lookup wins on copy-heavy text/code, MTP wins on free text, frequent transitions); they are not
fitted to any Strata measurement because none with per-round detail exists at commit 7dd5cf1.

Model per round (K_MAX = 7 drafts, the widest window kVerifyMaxT=8):
  - regime r (Markov chain per domain) -> MTP per-token hit rate pi ~ Beta around regime mean;
    MTP correctness c_j ~ Bern(pi); acc = first miss; reported draft prob p_j informative but miscalibrated.
  - prompt lookup (SuffixDrafter over prompt+output): proposal exists w.p. prop(r); match length drawn per regime;
    per-token hit rate q(r) (+ small bonus for long matches); k_prop = 7 mostly (continuation of the match source).
  - persistent pool (H1 extension a): lookup over previous requests of the same run. When the prompt lookup has
    nothing, the pool proposes w.p. pool_p(r) * ramp(request index) with hit rate pool_q(r).
  - agreement: common prefix of the MTP drafts and the lookup proposal (both right -> same token; both wrong -> same
    token w.p. 0.3, then stop).
"""
from __future__ import annotations
import json, math, random

K_MAX = 7

# regime: (mtp_pi_mean, lk_prop, lk_q, match_mu(log), pool_p, pool_q)
REGIMES = {
    "code": {
        "repeat":  (0.88, 0.75, 0.82, math.log(14), 0.20, 0.70),
        "novel":   (0.78, 0.35, 0.35, math.log(5),  0.30, 0.50),
    },
    "chat": {
        "free":    (0.68, 0.12, 0.30, math.log(4),  0.25, 0.45),
        "quote":   (0.80, 0.80, 0.85, math.log(15), 0.10, 0.60),
    },
    "edit": {
        "copy":    (0.85, 0.95, 0.95, math.log(30), 0.05, 0.40),
        "editpt":  (0.60, 0.90, 0.15, math.log(20), 0.05, 0.30),
        "free":    (0.70, 0.30, 0.40, math.log(5),  0.05, 0.40),
    },
}
# transition: regime -> list of (next, prob) per round, remaining mass = stay
TRANS = {
    "code": {"repeat": [("novel", 0.06)], "novel": [("repeat", 0.05)]},
    "chat": {"free": [("quote", 0.02)], "quote": [("free", 0.12)]},
    "edit": {"copy": [("editpt", 0.08)], "editpt": [("free", 0.35), ("copy", 0.25)], "free": [("copy", 0.20)]},
}
START = {"code": "novel", "chat": "free", "edit": "copy"}
PROMPT_LEN = {"code": (500, 4000), "chat": (100, 2000), "edit": (1500, 6000)}


def _beta_around(rng, mean, conc=20.0):
    return rng.betavariate(max(mean * conc, 0.05), max((1 - mean) * conc, 0.05))


def _correct(rng, rate, n):
    return [rng.random() < rate for _ in range(n)]


def _lcp(c):
    for i, x in enumerate(c):
        if not x:
            return i
    return len(c)


def _agree(cm, cl, rng):
    n = 0
    for a, b in zip(cm, cl):
        if a and b:
            n += 1
        elif not a and not b:
            return n + (1 if rng.random() < 0.3 else 0)
        else:
            return n
    return n


def _lookup(rng, q, mu):
    match = max(3, int(round(rng.lognormvariate(mu, 0.5))))
    qq = min(0.99, q + (0.03 if match >= 24 else 0.0))
    k = K_MAX if rng.random() < 0.8 else rng.randint(1, K_MAX - 1)
    c = _correct(rng, qq, k)
    return {"k": k, "match": match, "acc": _lcp(c)}, c


def generate(domain, n_requests=40, rounds=(60, 200), seed=0, run="synth"):
    rng = random.Random(f"{domain}-{seed}")
    out = []
    for req in range(n_requests):
        r = START[domain]
        pos = rng.randint(*PROMPT_LEN[domain])
        ramp = min(1.0, req / 10.0)   # the pool has seen `req` earlier requests
        for rnd in range(rng.randint(*rounds)):
            for nxt, p in TRANS[domain][r]:
                if rng.random() < p:
                    r = nxt
                    break
            pi_mean, prop, q, mu, pool_p, pool_q = REGIMES[domain][r]
            pi = _beta_around(rng, pi_mean)
            cm = _correct(rng, pi, K_MAX)
            probs = []
            for ok in cm:
                obs = rng.betavariate(6, 1.5) if ok else rng.betavariate(1.5, 3)
                probs.append(round(min(0.999, max(0.001, 0.5 * pi + 0.5 * obs)), 4))
            rec = {"schema": "strata.replay.v1", "synthetic": True, "run": f"{run}-{domain}-s{seed}",
                   "req": req, "domain": domain, "round": rnd, "pos": pos, "regime": r,
                   "mtp": {"k": K_MAX, "acc": _lcp(cm), "p": probs},
                   "lk": None, "lk_pool": None, "agree": 0, "agree_pool": 0}
            if rng.random() < prop:
                lk, cl = _lookup(rng, q, mu)
                rec["lk"] = lk
                rec["agree"] = _agree(cm, cl, rng)
                rec["lk_pool"] = dict(lk)
                rec["agree_pool"] = rec["agree"]
            elif rng.random() < pool_p * ramp:
                lk, cl = _lookup(rng, pool_q, math.log(6))
                rec["lk_pool"] = lk
                rec["agree_pool"] = _agree(cm, cl, rng)
            out.append(rec)
            # emitted tokens this round are policy dependent; positions advance by a typical 2.5 tokens
            pos += 2 + (1 if rng.random() < 0.5 else 0)
    return out


if __name__ == "__main__":
    import argparse, os
    ap = argparse.ArgumentParser(description="write SYNTHETIC replay traces (jsonl)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "traces"))
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--requests", type=int, default=40)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for d in REGIMES:
        for s in range(a.seeds):
            recs = generate(d, a.requests, seed=s)
            with open(os.path.join(a.out, f"SYNTHETIC_{d}_s{s}.jsonl"), "w") as f:
                for x in recs:
                    f.write(json.dumps(x, separators=(",", ":")) + "\n")
            print(f"SYNTHETIC {d} seed {s}: {len(recs)} rounds")
