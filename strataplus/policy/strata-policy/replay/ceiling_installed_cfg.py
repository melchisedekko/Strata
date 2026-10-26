"""ORACLE vs INSTALLED CONFIG (Strata Lead 06:55 CET): AL only, DESCRIPTIVE, hardware-independent, offline.
Method = replay/ceiling_long_window.py (sha256 27995db9…, unchanged; walk/lcp/boot/prompts copied, third sources dropped).
Per-round oracle: a = max over sources of accepted tokens (best source a posteriori), capped at n-i-1, round = a+1 tokens,
no memory across requests.  MTP acceptances from the traces (cand.mtp, Dmax=7) capped at the config's MTP draft limit;
lookup REGENERATED with the production SuffixDrafter (native sd_scan, min_match 3, max_match 64, max_k 16), fresh per
request on prompt + y[:i]; acceptance = lcp(cand[:L], y[p:p+L]) = min(acc16, L) (proposal is a prefix-copy, so the
L-token proposal is the first L tokens of the 16-token one; checked: min(acc16,7) == trace lk_acc).
Configurations (rows = verify window T = 1 + drafts; strata-src @7dd5cf1 generate.cpp):
  a  installed: setup writes --spec 4; L3208-3211 (suffix_draft on, mtp_max_t==0): mtp_max_t = 4, spec = min(4+2,8) = 6;
     L11173-11174 mtp.set_max_drafts(S_mtp-1) -> MTP <= 3 drafts (4 rows); L14897 sfx.propose(S-1) -> lookup <= 5 (6 rows)
  b  T<=8 today: MTP <= 7, lookup <= 7   (must reproduce 'two' / 'two8' of the previous reports)
  c  lookup16: MTP <= 7, lookup <= 16
  d  lookup12: MTP <= 7, lookup <= 12
Bootstrap B=2000 seed 0 over sessions (= requests here).  usage: script OUTDIR"""
import json, os, sys, hashlib
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
CFG = {"a": (3, 5), "b": (7, 7), "c": (7, 16), "d": (7, 12)}   # (MTP draft cap, lookup cap)
PREV_TWO = {"tune|code": 6.708791208791209, "holdout|code": 6.831417624521073, "tune|chat": 2.892523364485981,
            "holdout|chat": 3.290235081374322, "tune|edit": 5.981308411214953, "holdout|edit": 6.435677530017153}  # ceiling_third_source.json 'two'


def prompts(path):
    P = {}
    for l in open(path):
        o = json.loads(l)
        if o.get("type") == "request" and o.get("rep", 0) == 0:
            P[o["req_id"]] = o["prompt_ids"]
    return P


def walk(q, acc16, mcap, lcap):
    n = q["n"]; i = 0; R = 0; hist = np.zeros(17, int); tok_by_a = np.zeros(17, int); win = np.zeros((17, 2), int)
    while i < n:
        am = min(int(q["mtp_acc"][i]), mcap); al = min(int(acc16[i]), lcap); cap = n - i - 1
        a = min(max(am, al), cap)
        hist[a] += 1; tok_by_a[a] += a + 1; win[a, 0 if min(al, cap) == a else 1] += 1   # tie -> lookup
        R += 1; i += a + 1
    return n, R, hist, tok_by_a, win


def boot_multi(rows, clusters, B=2000, seed=0):
    keys = sorted(set(clusters)); g = {k: [j for j, x in enumerate(clusters) if x == k] for k in keys}
    N = {c: np.array([sum(rows[c][j][0] for j in g[k]) for k in keys], float) for c in rows}
    D = {c: np.array([sum(rows[c][j][1] for j in g[k]) for k in keys], float) for c in rows}
    s = np.random.default_rng(seed).integers(0, len(keys), (B, len(keys)))
    AL = {c: N[c].sum() / D[c].sum() for c in rows}; ALb = {c: N[c][s].sum(1) / D[c][s].sum(1) for c in rows}
    out = {}
    for x, y in (("b", "a"), ("c", "a"), ("d", "a"), ("c", "b"), ("d", "b")):
        v = ALb[x] / ALb[y] - 1
        out["%s_vs_%s" % (x, y)] = (float(AL[x] / AL[y] - 1), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (ALb["d"] - ALb["b"]) / (ALb["c"] - ALb["b"])
    pt = (AL["d"] - AL["b"]) / (AL["c"] - AL["b"]) if AL["c"] != AL["b"] else None
    vv = v[np.isfinite(v)]
    out["share_gain_c_from_le12"] = (pt, float(np.percentile(vv, 2.5)) if len(vv) else None,
                                     float(np.percentile(vv, 97.5)) if len(vv) else None, int(len(vv)))
    return AL, out


OUT = {"label": "ORACOLO vs CONFIG INSTALLATA: solo AL, descrittivo, tetto superiore; MTP dalle tracce (proxy llama.cpp 2B); "
                "lookup rigenerato fino a 16 sui token di riferimento completi; niente tok/s",
       "files_sha256": {k: sha(p) for k, p in FILES.items()}, "script_sha256": sha(os.path.abspath(__file__)),
       "configs": {k: {"mtp_max_drafts": v[0], "lookup_max_tokens": v[1]} for k, v in CFG.items()},
       "strata_src_rev": "7dd5cf18e68c639a8773e096c5c79f971ea2a9f5", "results": {}}
cache = {}
for dom in ("code", "chat", "edit"):
    for split in ("tune", "holdout"):
        path = FILES["tune"] if split == "tune" else FILES["holdout_" + dom]
        if path not in cache:
            cache[path] = (load_tf(path), prompts(path))
        R, P = cache[path]
        reqs = [q for q in R if q["domain"] == dom]
        clusters = [q["session"] for q in reqs]
        rows = {c: [] for c in CFG}; H = {c: np.zeros(17, int) for c in CFG}; TK = {c: np.zeros(17, int) for c in CFG}
        WIN = {c: np.zeros((17, 2), int) for c in CFG}
        scan_hist = np.zeros(17, int); scan_hist_cap = np.zeros(17, int); mism = 0; npos = 0
        for q in reqs:
            y = q["y"]; n = q["n"]
            lk = NativeSuffixDrafter(3, 64, 1 << 15); lk.append(np.asarray(P[q["req"]], np.int32))
            _, _, acc16, _ = lk.scan(y, 16, want_tokens=False)
            acc16 = np.asarray(acc16)
            mism += int(np.sum(np.minimum(acc16, 7) != q["lk_acc"])); npos += n
            scan_hist += np.bincount(acc16, minlength=17)[:17]
            scan_hist_cap += np.bincount(np.minimum(acc16, n - 1 - np.arange(n)), minlength=17)[:17]
            for c, (mc, lc) in CFG.items():
                nn, rr, h, tk, w = walk(q, acc16, mc, lc)
                rows[c].append((nn, rr)); H[c] += h; TK[c] += tk; WIN[c] += w
        AL, D = boot_multi(rows, clusters)
        key = "%s|%s" % (split, dom)
        res = dict(n_req=len(reqs), positions=npos, AL=AL, deltas=D, b_equals_prev_two=bool(abs(AL["b"] - PREV_TWO[key]) < 1e-12),
                   lookup16_vs_trace_cap7_mismatch=mism,
                   scan_acc16_hist=scan_hist.tolist(), scan_acc16_hist_capped_n_i_1=scan_hist_cap.tolist(),
                   walk_c_rounds_by_a=H["c"].tolist(), walk_c_tokens_by_a=TK["c"].tolist(),
                   walk_c_winner_by_a_lookup_mtp=WIN["c"].tolist(), walk_d_rounds_by_a=H["d"].tolist(),
                   walk_b_rounds_by_a=H["b"].tolist(), rounds={c: int(sum(r[1] for r in rows[c])) for c in CFG},
                   tokens=int(sum(r[0] for r in rows["a"])))
        OUT["results"][key] = res
        print(key, {c: round(v, 4) for c, v in AL.items()}, "b==prev", res["b_equals_prev_two"], "mism", mism,
              {k: tuple(None if x is None else round(x * 100, 2) for x in v[:3]) for k, v in D.items()}, flush=True)
json.dump(OUT, open(os.path.join(OUTD, "ceiling_installed_cfg.json"), "w"), indent=1, default=float)
