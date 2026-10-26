"""CEILING STUDY (Strata Lead GO 06:42 CET + steering 06:43): DESCRIPTIVE, offline, no model.  tok/s ESTIMATED.
Per-round ORACLE (teacher-forced traces, greedy y): each round takes the source with max accepted tokens,
window d<=7 (DMAX) for every source, round yields a+1 tokens.  No memory across requests (per-request ceiling,
H2a with one request) except the agent_edit 'H2a session pool' variant (earlier turns of the same session indexed).
Sources:
  mtp     : cand.mtp tokens (proxy llama.cpp 2B), acc = LCP (postprocess.load_tf mtp_acc)
  lookup  : production NativeSuffixDrafter(min_match=3,max_match=64) per request (load_tf lk_*); session pool = load_tf pl_*
  suffix  : SuffixDecoding (arXiv 2411.04975) re-implemented from the documented algorithm (vLLM config/speculative.py
            defaults max_tree_depth=24, max_spec_factor=1.0, min_token_prob=0.1; ArcticInference docs).  NOT the
            ArcticInference source (no local clone): per-request suffix index over prompt+y[:i]; for every match length
            L (1..23) greedy most-frequent path from the matched node, prob = prod(child_count/node_count) >= 0.1,
            max_spec = min(7, floor(1.0*L), 24-L); best path by score = sum of path probs (tie -> longer L).
  ngram_mod: llama.cpp common_ngram_mod, /workspace/llama.cpp @d327bf1f: hash ngram-mod.cpp L15-25 (LCG 6364136223846793005,
            size_t overflow, % 4*1024*1024 entries, speculative.cpp L2106), add L27-35 (last writer wins), begin()
            speculative.cpp L2124-2150 (adds prompt n-grams i < |prompt|-n), draft_one L2152-2206 (chunked add only when
            i_last+32 < cur_len, key = last n-1 prompt tokens + id_last, stop on EMPTY, clear if < n_min),
            accept L2226-2251 (reset after 5 rounds with f_acc<0.25; called only when the oracle picks ngram_mod,
            else is_other).  Defaults common.h L360-363: n_match=24, n_max=64, n_min=48 -> n_max clipped to the window 7;
            variant A n_min=min(48,7)=7 ; variant B n_min=1 (sensitivity).
Cost M-real: Profile.cost(T, d=max(d,1) MTP drafts, klu) ; T=a+1 ; MTP chosen -> d=max(a,1), other source -> d=1;
  klu = lookup proposal length (+ third-source proposal length in the 3-source oracle).  Ties -> cheaper source.
Band: P1/P2/P4 x rho {0.059,0.0791,0.0992,0.1193,0.1394}, cost V1 (cost_p4_cpu.json).  Bootstrap B=2000 seed 0 over
requests (agent_edit: over sessions).  usage: script OUTDIR"""
import json, os, sys, hashlib, bisect, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strata_sim.sim2 import Profile, load_p4, S_P1, p2_s
from strata_sim.postprocess import load_tf

OUTD = sys.argv[1]; os.makedirs(OUTD, exist_ok=True)
TR = "/workspace/strata-plus/traces/v1.1"
FILES = {"tune": os.path.join(TR, "tf_d7_p30.jsonl"), "agent": os.path.join(TR, "agent_turns_bench_tf_d7.jsonl")}
for d in ("code", "chat", "edit"):
    FILES["holdout_" + d] = os.path.join(TR, "holdout_%s_tf_d7.jsonl" % d)
COSTP = "/workspace/strata-plus/traces/cost_p4_cpu.json"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
W = 7; SEP = -1
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

    def __init__(self, seq):
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
            ms = min(W, int(1.0 * L), 24 - L); path, pr, sc = [], 1.0, 0.0
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
    def __init__(self, n=24, n_max=W, n_min=W):
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


def walk(q, mode, third, lkey, ctx):
    """mode 'two' or 'three'. returns per-round list of (T, d, klu) and N."""
    y = q["y"].tolist(); n = q["n"]; i = 0; rounds = []; c, lo, plen = ctx
    if third == "ngA" or third == "ngB":
        ng = ctx_ng[q["req"]]
        ng.begin(c, lo, plen)
    while i < n:
        am, al = int(q["mtp_acc"][i]), int(q[lkey + "_acc"][i]); klu = int(q[lkey + "_k"][i])
        cands = [(am, "mtp"), (al, "lk")]
        prop = None
        if mode == "three":
            N = lo + plen + i
            prop = sfx_of[q["req"]].propose(N, lo) if third == "suffix" else ng.draft(c, lo, N)
            cands.append((lcp(prop, y, i), "third")); klu += len(prop)
        cap = n - i - 1
        a = min(max(x for x, _ in cands), cap)
        # ties -> cheaper: non-MTP source costs 1 draft, MTP costs max(a,1)
        src = "mtp"
        for x, s in cands:
            if s != "mtp" and min(x, cap) == a and a >= 1:
                src = s; break
        if mode == "three" and third in ("ngA", "ngB"):
            ng.accept(min(cands[2][0], cap), src != "third")
        d = max(a, 1) if src == "mtp" else 1
        rounds.append((a + 1, d, klu, src))
        i += a + 1
    return rounds


def tps(rows, prof):
    N = sum(r[0] for r in rows); C = sum(sum(prof.cost(T, d, k) for T, d, k, _ in r[1]) for r in rows)
    return N / C


def boot(rows2, rows3, clusters, stat, B=2000, seed=0):
    keys = sorted(set(clusters)); g = {k: [] for k in keys}
    for j, k in enumerate(clusters):
        g[k].append(j)
    a2 = np.array([[sum(stat(r, x) for x in ([rows2[j] for j in g[k]])) for k in keys]]) if False else None
    def agg(rows):
        num = np.array([sum(stat(rows[j])[0] for j in g[k]) for k in keys]); den = np.array([sum(stat(rows[j])[1] for j in g[k]) for k in keys])
        return num, den
    n2, d2 = agg(rows2); n3, d3 = agg(rows3)
    pt = (n3.sum() / d3.sum()) / (n2.sum() / d2.sum()) - 1
    rng = np.random.default_rng(seed); s = rng.integers(0, len(keys), (B, len(keys)))
    v = (n3[s].sum(1) / d3[s].sum(1)) / (n2[s].sum(1) / d2[s].sum(1)) - 1
    return float(pt), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


P4 = load_p4(COSTP); SH = {"P1": S_P1, "P2": p2_s(), "P4": P4.s}
PROFS = [Profile("%s|rho%.4f" % (sn, r), s, r, P4.rho_lu, "band") for sn, s in SH.items()
         for r in (0.059, 0.0791, 0.0992, 0.1193, 0.1394)]
THIRDS = ["suffix", "ngA", "ngB"]
OUT = {"label": "STUDIO DEL TETTO, descrittivo, offline, oracolo per round (limite superiore); tok/s STIMATI (costo V1 M-real); "
                "mtp dal proxy llama.cpp 2B; nessuna sessione agentica reale (agent_edit = edit_np costruito, licenza in verifica da Bench, solo calcolo offline)",
       "files_sha256": {k: sha(p) for k, p in FILES.items()}, "cost_sha256": sha(COSTP), "script_sha256": sha(os.path.abspath(__file__)),
       "llama_cpp_rev": "d327bf1f0780f87b8c01b367b61853b0c291d7c4", "results": {}}

sets = []
for d in ("code", "chat", "edit"):
    sets.append(("tune", d, FILES["tune"], "domain", "lk", False))
    sets.append(("holdout", d, FILES["holdout_" + d], "domain", "lk", False))
sets.append(("tune", "agent_edit", FILES["agent"], "session", "lk", False))
sets.append(("tune", "agent_edit_H2a_pool", FILES["agent"], "session", "pl", True))
cache = {}
for split, dom, path, scope, lkey, pooled in sets:
    if (path, scope) not in cache:
        cache[(path, scope)] = (load_tf(path, pool_scope=scope), prompts(path))
    R, (PR, META) = cache[(path, scope)]
    reqs = [q for q in R if q["domain"] == dom.replace("_H2a_pool", "")]
    reqs.sort(key=lambda q: (str(META[q["req"]][0]), META[q["req"]][1])) if pooled else None
    clusters = [q["session"] for q in reqs]
    # contexts: per request (fresh) or session concatenation with SEP between turns
    sfx_of, ctxs, ctx_ng_by = {}, {}, {}
    res = {"n_req": len(reqs), "n_clusters": len(set(clusters)), "lookup": "per-request" if lkey == "lk" else "session pool (load_tf pl_*)"}
    rows = {"two": []}; rows.update({t: [] for t in THIRDS})
    if pooled:
        bys = collections.OrderedDict()
        for q in reqs:
            bys.setdefault(q["session"], []).append(q)
        for s, qs in bys.items():
            seq = []; los = {}
            for q in qs:
                if seq:
                    seq.append(SEP)
                los[q["req"]] = (len(seq), len(PR[q["req"]])); seq += list(PR[q["req"]]) + q["y"].tolist()
            sx = Suffix(seq)
            for q in qs:
                sfx_of[q["req"]] = sx; ctxs[q["req"]] = (seq,) + los[q["req"]]
            ctx_ng_by[s] = {"ngA": NgramMod(n_min=W), "ngB": NgramMod(n_min=1)}
    else:
        for q in reqs:
            seq = list(PR[q["req"]]) + q["y"].tolist()
            sfx_of[q["req"]] = Suffix(seq); ctxs[q["req"]] = (seq, 0, len(PR[q["req"]]))
    for q in reqs:
        rows["two"].append((q["n"], walk(q, "two", None, lkey, ctxs[q["req"]])))
    for t in THIRDS:
        for q in reqs:
            if t != "suffix":
                ctx_ng = {q["req"]: (ctx_ng_by[q["session"]][t] if pooled else NgramMod(n_min=W if t == "ngA" else 1))}
                globals()["ctx_ng"] = ctx_ng
            rows[t].append((q["n"], walk(q, "three", t, lkey, ctxs[q["req"]])))
    alstat = lambda r: (r[0], len(r[1]))
    AL = {k: sum(r[0] for r in v) / sum(len(r[1]) for r in v) for k, v in rows.items()}
    res["AL"] = AL
    res["src_share"] = {k: dict(collections.Counter(s for r in v for *_, s in r[1])) for k, v in rows.items()}
    res["AL_delta_vs_two"] = {t: boot(rows["two"], rows[t], clusters, alstat) for t in THIRDS}
    res["tps"] = {}
    for t in THIRDS:
        cells = []
        for p in PROFS:
            cstat = lambda r, p=p: (r[0], sum(p.cost(T, d, k) for T, d, k, _ in r[1]))
            ci = boot(rows["two"], rows[t], clusters, cstat)
            cells.append(dict(cell=p.name, tps_two=tps(rows["two"], p), tps_three=tps(rows[t], p), delta=ci))
        cells.sort(key=lambda x: x["delta"][0])
        res["tps"][t] = dict(cells=cells, median_cell=cells[len(cells) // 2])
    OUT["results"]["%s|%s" % (split, dom)] = res
    print(split, dom, {k: round(v, 4) for k, v in AL.items()}, {t: tuple(round(x * 100, 2) for x in res["AL_delta_vs_two"][t]) for t in THIRDS}, flush=True)
json.dump(OUT, open(os.path.join(OUTD, "ceiling_third_source.json"), "w"), indent=1, default=float)
