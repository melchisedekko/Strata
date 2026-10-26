"""LONG-WINDOW ORACLE (Strata Lead 06:50 CET + steering 06:51): AL only, DESCRIPTIVE, hardware-independent, offline.
Logic reused from replay/ceiling_third_source.py (sha256 550f480a…, unchanged; classes Suffix / NgramMod copied with the
window as a parameter).  Per-round oracle, a = max over sources of accepted tokens, round yields a+1 tokens, no memory
across requests.  MTP stays at Dmax=7 (trace cand.mtp, load_tf mtp_acc).  Non-MTP sources propose up to 16 tokens
(window 16+1); acceptance = lcp(cand[:16], y[p:p+16]) with y = full greedy reference of the request (ref_tokens).
  lookup  : REGENERATED here with the production SuffixDrafter (native sd_scan, min_match 3, max_match 64, max_k 16;
            strata-src src/spec/suffix_drafter.cpp L64-86 copies up to max_k tokens), fresh per request on prompt+y[:i];
            sanity: min(acc16,7) must equal load_tf lk_acc (recorded lookup capped at 7).
  suffix  : SuffixDecoding re-implementation (see ceiling_third_source.py), max_spec = min(16, floor(L), 24-L).
  ngram_mod: llama.cpp common_ngram_mod @d327bf1f (see ceiling_third_source.py), n_match 24, n_max 16,
            A: n_min = min(48,16) = 16 (main), B: n_min = 1 (sensitivity only).
Configurations (no others): two8 = MTP + lookup<=7 (T<=8); two16 = MTP + lookup<=16; sfx16 = two16 + suffix<=16;
ng16 = two16 + ngram_mod<=16 (A; B sensitivity).  Bootstrap B=2000 seed 0 over requests.  usage: script OUTDIR"""
import json, os, sys, hashlib, bisect, collections
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
W = 16; SEP = -1
M64 = (1 << 64) - 1; MULT = 6364136223846793005; MODSZ = 4 * 1024 * 1024


def prompts(path):
    P, meta = {}, {}
    for l in open(path):
        o = json.loads(l)
        if o.get("type") == "request" and o.get("rep", 0) == 0:
            P[o["req_id"]] = o["prompt_ids"]; meta[o["req_id"]] = (o.get("session_id"), o.get("turn", 0))
    return P, meta


class Suffix:
    """index over seq (full, teacher-forced); only positions < N are ever read at query time."""
    LMAX = 23

    def __init__(self, seq, W):
        self.W = W
        self.c = np.asarray(seq, np.int64); c = self.c.tolist(); self.cl = c
        self.idx = [None] + [collections.defaultdict(list) for _ in range(self.LMAX)]
        for j in range(1, len(c) + 1):          # pattern c[j-L:j], continuation c[j]
            for L in range(1, min(self.LMAX, j) + 1):
                t = tuple(c[j - L:j])
                if SEP in t:
                    break
                self.idx[L][t].append(j)

    def propose(self, N, lo):
        """N = known length; lo = start of current request context (patterns may not cross it backwards)."""
        c = self.cl; best, bsc = [], 0.0
        for L in range(1, min(self.LMAX, N - lo) + 1):
            lst = self.idx[L].get(tuple(c[N - L:N]))
            if not lst:
                break
            occ = np.asarray(lst[:bisect.bisect_left(lst, N)], np.int64)
            if occ.size == 0:
                break
            ms = min(self.W, int(1.0 * L), 24 - L); path, pr, sc = [], 1.0, 0.0
            while len(path) < ms:
                occ = occ[occ < N]
                if occ.size == 0:
                    break
                nxt = self.c[occ]; nxt_v = nxt[nxt != SEP]
                if nxt_v.size == 0:
                    break
                u, cnt = np.unique(nxt_v, return_counts=True)
                mx = cnt.max(); cand = u[cnt == mx]
                if cand.size > 1:                  # tie -> most recent occurrence
                    tok = int(nxt[np.isin(nxt, cand)][-1])
                else:
                    tok = int(cand[0])
                pr *= mx / occ.size
                if pr < 0.1:
                    break
                path.append(tok); sc += pr; occ = occ[nxt == tok] + 1
            if path and sc >= bsc:
                best, bsc = path, sc
        return best


class NgramMod:
    def __init__(self, n=24, n_max=16, n_min=16):
        self.n, self.n_max, self.n_min = n, n_max, n_min; self.reset_all()

    def reset_all(self):
        self.tab = {}; self.i_last = 0; self.n_draft_last = 0; self.n_low = 0

    def idx(self, c, j):
        r = 0
        for i in range(self.n):
            r = (r * MULT + (c[j + i] & 0xFFFFFFFFFFFFFFFF)) & M64
        return r % MODSZ

    def add(self, c, j):
        self.tab[self.idx(c, j)] = c[j + self.n]

    def begin(self, c, lo, plen):            # prompt = c[lo:lo+plen]; mod shared (not reset) like the server
        self.i_last = 0; self.n_draft_last = 0
        if plen < self.n:
            return
        for i in range(plen - self.n):
            self.add(c, lo + i)
        self.i_last = plen - self.n          # relative to lo (occupancy reset f>0.25 never reached here)

    def draft(self, c, lo, N):
        """prompt = c[lo:N-1], id_last = c[N-1]"""
        self.n_draft_last = 0; n = self.n; cur = N - 1 - lo
        if cur < n:
            return []
        if self.i_last + 32 < cur:
            for i in range(self.i_last, cur - n):
                self.add(c, lo + i)
            self.i_last = cur - n
        res = list(c[N - n:N])
        for i in range(self.n_max):
            t = self.tab.get(self.idx(res, i), SEP)
            if t == SEP:
                if i < self.n_min:
                    return []
                break
            res.append(t)
        out = res[n:]; self.n_draft_last = len(out)
        return out

    def accept(self, nacc, is_other):
        if is_other or self.n_draft_last <= 0:
            return
        if nacc / self.n_draft_last < 0.25:
            self.n_low += 1
            if self.n_low >= 5:
                self.tab = {}; self.n_low = 0; self.i_last = 0
        else:
            self.n_low = 0


def lcp(a, y, i):
    k = 0
    while k < len(a) and i + k < len(y) and a[k] == y[i + k]:
        k += 1
    return k




def lcp(a, y, i, w=W):
    k = 0
    while k < len(a) and k < w and i + k < len(y) and a[k] == y[i + k]:
        k += 1
    return k


def walk(q, cfg, lk16, ctx, sx=None, ng=None):
    y = q["y"].tolist(); n = q["n"]; i = 0; R = 0; c, lo, plen = ctx
    if ng is not None:
        ng.begin(c, lo, plen)
    while i < n:
        am = int(q["mtp_acc"][i]); al = int(lk16[i]) if cfg != "two8" else min(int(lk16[i]), 7)
        a3 = -1; prop = None
        if sx is not None:
            prop = sx.propose(lo + plen + i, lo)
        elif ng is not None:
            prop = ng.draft(c, lo, lo + plen + i)
        if prop is not None:
            a3 = lcp(prop, y, i)
        cap = n - i - 1
        a = min(max(am, al, a3), cap)
        if ng is not None:
            ng.accept(min(a3, cap), not (a >= 1 and min(a3, cap) == a and min(al, cap) < a))   # = ceiling_third_source tie rule (lookup first, then third, before MTP)
        R += 1; i += a + 1
    return n, R


def boot(r0, r1, clusters, B=2000, seed=0):
    keys = sorted(set(clusters)); g = {k: [j for j, x in enumerate(clusters) if x == k] for k in keys}
    agg = lambda rr: (np.array([sum(rr[j][0] for j in g[k]) for k in keys], float), np.array([sum(rr[j][1] for j in g[k]) for k in keys], float))
    n0, d0 = agg(r0); n1, d1 = agg(r1)
    pt = (n1.sum() / d1.sum()) / (n0.sum() / d0.sum()) - 1
    s = np.random.default_rng(seed).integers(0, len(keys), (B, len(keys)))
    v = (n1[s].sum(1) / d1[s].sum(1)) / (n0[s].sum(1) / d0[s].sum(1)) - 1
    return float(pt), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


OUT = {"label": "ORACOLO A FINESTRA LUNGA: solo AL, descrittivo, limite superiore; MTP a Dmax=7 dalle tracce (proxy llama.cpp 2B); "
                "lookup/Suffix/ngram_mod fino a 16 rigenerati sui token di riferimento completi",
       "files_sha256": {k: sha(p) for k, p in FILES.items()}, "script_sha256": sha(os.path.abspath(__file__)),
       "llama_cpp_rev": "d327bf1f0780f87b8c01b367b61853b0c291d7c4", "y_check": {}, "results": {}}
sets = [(s, d, FILES["tune"] if s == "tune" else FILES["holdout_" + d]) for d in ("code", "chat", "edit") for s in ("tune", "holdout")]
cache = {}
for split, dom, path in sets:
    if path not in cache:
        R = load_tf(path); P, _ = prompts(path)
        raw = {}
        for l in open(path):
            o = json.loads(l)
            if o.get("rep", 0) != 0:
                continue
            if o.get("type") == "request":
                raw.setdefault(o["req_id"], {})["req"] = o
            elif o.get("type") == "round":
                raw.setdefault(o["req_id"], {}).setdefault("pos", set()).add(o.get("gen_index", o.get("pos")))
        cache[path] = (R, P, raw)
    R, P, raw = cache[path]
    reqs = [q for q in R if q["domain"] == dom]
    # y completeness: len(ref_tokens) == recorded output_tokens, == number of rounds, rounds cover 0..n-1, output sha
    yc = []
    for q in reqs:
        o = raw[q["req"]]["req"]; pos = raw[q["req"]].get("pos", set())
        ot = o.get("output_tokens"); osha = o.get("ref_output_sha256") or o.get("output_sha256")
        yc.append(dict(req=q["req"], n=q["n"], len_ref=len(o.get("ref_tokens") or []), output_tokens=ot,
                       rounds_cover=pos >= set(range(q["n"])), n_rounds=len(pos), max_new=128))
    OUT["y_check"]["%s|%s" % (split, dom)] = dict(
        n_req=len(yc), all_len_ref_eq_output_tokens=all(x["len_ref"] == x["output_tokens"] for x in yc),
        all_rounds_cover=all(x["rounds_cover"] for x in yc), n_len_lt_128=sum(x["n"] < 128 for x in yc),
        min_n=min(x["n"] for x in yc), max_n=max(x["n"] for x in yc))
    clusters = [q["session"] for q in reqs]
    rows = {k: [] for k in ("two8", "two16", "sfx16", "ng16A", "ng16B")}; mism = 0; pos_ge8 = 0; pos_all = 0
    for q in reqs:
        Pq = P[q["req"]]; y = q["y"]
        lk = NativeSuffixDrafter(3, 64, 1 << 15); lk.append(np.asarray(Pq, np.int32))
        k16, m16, acc16, _ = lk.scan(y, W, want_tokens=False)
        mism += int(np.sum(np.minimum(acc16, 7) != q["lk_acc"]))
        pos_ge8 += int(np.sum(acc16 >= 8)); pos_all += len(acc16)
        seq = list(Pq) + y.tolist(); ctx = (seq, 0, len(Pq))
        rows["two8"].append(walk(q, "two8", acc16, ctx))
        rows["two16"].append(walk(q, "two16", acc16, ctx))
        rows["sfx16"].append(walk(q, "sfx16", acc16, ctx, sx=Suffix(seq, W)))
        rows["ng16A"].append(walk(q, "ng16", acc16, ctx, ng=NgramMod(n_max=W, n_min=16)))
        rows["ng16B"].append(walk(q, "ng16", acc16, ctx, ng=NgramMod(n_max=W, n_min=1)))
    AL = {k: sum(r[0] for r in v) / sum(r[1] for r in v) for k, v in rows.items()}
    res = dict(n_req=len(reqs), AL=AL, lookup16_vs_trace_cap7_mismatch_positions=mism,
               lookup16_positions_acc_ge8=pos_ge8, positions=pos_all,
               delta_vs_two8={k: boot(rows["two8"], rows[k], clusters) for k in rows if k != "two8"},
               third_increment_vs_two16={k: boot(rows["two16"], rows[k], clusters) for k in ("sfx16", "ng16A", "ng16B")})
    OUT["results"]["%s|%s" % (split, dom)] = res
    print(split, dom, {k: round(v, 4) for k, v in AL.items()}, "mism", mism,
          {k: tuple(round(x * 100, 2) for x in v) for k, v in res["delta_vs_two8"].items()}, flush=True)
json.dump(OUT, open(os.path.join(OUTD, "ceiling_long_window.json"), "w"), indent=1, default=float)
