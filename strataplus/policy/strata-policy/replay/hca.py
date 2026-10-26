"""H-CA (configurazione dello speculative decoding in base al contenuto), replay su tracce PROXY CPU v1.1 (Qwen3.5-2B-MTP).
Protocollo fissato in run_hca.json (sha256 asserito sotto). Due modalita':
  smoke  : legge e verifica le tracce (sha, forme, EOS, lookup ricalcolato 7 vs 15, decodifica, fence/segmenti, feature
           causali disponibili). NESSUNA metrica di risultato (niente AL, tok/s, accettanze aggregate).
  eval   : la valutazione H-CA del run file.  Richiede --authorized (autorizzazione dell'utente).  In fase 1 NON eseguita.
usage: nice -n 19 env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 hca.py smoke OUT.json
       ... python3 hca.py eval OUTDIR --authorized"""
import json, os, re, sys, struct, hashlib, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strata_sim.native import NativeDraftPolicy, NativeSuffixDrafter
from strata_sim import sim2

RUN = os.path.join(HERE, "run_hca.json")
RUN_SHA = "ea2bed9c1438175c279c291652a6e9dd552e14b24d694320befc9338249bf50b"
TR = "/workspace/strata-plus/traces/v1.1"
GGUF = "/workspace/strata-bench/models/qwen35-2b-mtp-q4_k_m.gguf"
FILES = {"tune": ("tf_d7_p30.jsonl", "87efe507324b2a79b89c21a6736f1478094bf53385d9471694dc71b291d9abfa"),
         "holdout_code": ("holdout_code_tf_d7.jsonl", "a9e247b2fd9a0da14517459f028d2b9e85195955895855459c3c924f0e37f603"),
         "holdout_chat": ("holdout_chat_tf_d7.jsonl", "b5380c42b9155571054958f00cb501ca7a309feaf8e9cc058f54bd00692b4588"),
         "holdout_edit": ("holdout_edit_tf_d7.jsonl", "d9a48386945b1131766cb8b38a1572bc2d3992d8b5bd8291ecbe85c79f3e94ef")}
MANIFEST_SHA = "34bdc195a1ec18824cc5497f4e2c98ef138803672f651cc4db2c045901f68d3f"
GGUF_SHA = "18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b"
EOG = 248046                      # <|im_end|> = tokenizer.ggml.eos_token_id
DOMAINS = ("code", "chat", "edit")
RULES = ("fixed", 0.3, 0.5, 0.7, 0.9, "cost")
GRID = [(S, Sm, r) for S in range(2, 9) for Sm in range(2, S + 1) for r in RULES]          # 168, ordine del run file
N_LK = 8; THETA_LK = (0.25, 0.5, 0.75); THETA_P = (0.5, 0.7, 0.9); NFOLD = 5; MAXA = 8
RHO = {"flat": 0.19617814763445762, "steep": 0.538461538461537}
FENCE = re.compile(rb"(?m)^[ \t]*```")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
unl = lambda v: v[2] if isinstance(v, list) and len(v) == 3 and v[0] == "list" else v


# ------------------------------------------------------------------ vocab (parser GGUF minimale, nessuna installazione)
def gguf_tokens(path):
    SZ = {0: 'B', 1: 'b', 2: 'H', 3: 'h', 4: 'I', 5: 'i', 6: 'f', 7: '?', 10: 'Q', 11: 'q', 12: 'd'}
    f = open(path, "rb"); assert f.read(4) == b"GGUF"
    _, _, nkv = struct.unpack("<IQQ", f.read(20)); out = {}
    def s():
        n, = struct.unpack("<Q", f.read(8)); return f.read(n).decode("utf-8", "surrogateescape")
    def val(t):
        if t == 8: return s()
        if t == 9:
            et, n = struct.unpack("<IQ", f.read(12)); return [val(et) for _ in range(n)]
        fm = "<" + SZ[t]; return struct.unpack(fm, f.read(struct.calcsize(fm)))[0]
    for _ in range(nkv):
        k = s(); t, = struct.unpack("<I", f.read(4)); v = val(t)
        if k.startswith("tokenizer.ggml.") and k in ("tokenizer.ggml.tokens", "tokenizer.ggml.model", "tokenizer.ggml.pre",
                                                    "tokenizer.ggml.eos_token_id"):
            out[k] = v
        if len(out) == 4: break
    return out


def byte_decoder():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]; n = 0
    for b in range(256):
        if b not in bs: bs.append(b); cs.append(256 + n); n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


class Vocab:
    def __init__(self):
        assert sha(GGUF) == GGUF_SHA
        kv = gguf_tokens(GGUF)
        assert kv["tokenizer.ggml.model"] == "gpt2" and kv["tokenizer.ggml.eos_token_id"] == EOG
        bd = byte_decoder(); self.b = []
        for t in kv["tokenizer.ggml.tokens"]:
            self.b.append(bytes(bd[c] for c in t) if all(c in bd for c in t) else t.encode("utf-8", "surrogateescape"))

    def pieces(self, ids):
        return [self.b[int(t)] for t in ids]


def fences(pieces):
    """linee-fence nel testo concatenato: per ognuna (indice del token che completa il terzo backtick, info string)."""
    txt = b"".join(pieces); ends = np.cumsum([len(p) for p in pieces]) if pieces else np.zeros(0, int); out = []
    for m in FENCE.finditer(txt):
        e = m.end() - 1                                        # byte del terzo backtick
        j = int(np.searchsorted(ends, e, side="right"))        # token che contiene quel byte
        nl = txt.find(b"\n", m.end()); info = txt[m.end(): nl if nl >= 0 else len(txt)].strip()[:32]
        out.append((j, info.decode("utf-8", "replace")))
    return out


# ------------------------------------------------------------------ caricamento tracce
def load(key, voc):
    fn, h = FILES[key]; p = os.path.join(TR, fn); assert sha(p) == h, key
    req, rounds, ends, order = {}, collections.defaultdict(list), {}, []
    for l in open(p):
        o = json.loads(l); t = o.get("type"); rk = (o.get("req_id"), o.get("rep", 0))
        if t == "request": req[rk] = o; order.append(rk)
        elif t == "round": rounds[rk].append(o)
        elif t == "request_end": ends[rk] = o
    Q = []
    for idx, rk in enumerate(order):
        r = req[rk]; y = [int(t) for t in unl(ends[rk]["output_ids"])]; n = len(y); pr = [int(t) for t in unl(r["prompt_ids"])]
        R = sorted(rounds[rk], key=lambda o: o["pos"])
        assert n == int(r["output_tokens"]) and [o["pos"] for o in R] == list(range(n))
        assert sum(o["committed"] for o in R) == n, "ERRATA EOS: committed oltre la fine"
        assert EOG not in y[:-1], "ERRATA EOS: EOG dentro y"
        mt = np.array([o["cand"]["mtp"]["tokens"] for o in R], np.int64)
        mp = np.array([o["cand"]["mtp"]["probs"] for o in R], np.float64)
        assert mt.shape == (n, 7) and mp.shape == (n, 7) and np.isfinite(mp).all()
        macc = np.array([int(o["acc"]["mtp"]) for o in R], np.int64)
        sd = NativeSuffixDrafter(3, 64, 1 << 15); sd.append(np.asarray(pr, np.int32))
        k15, m15, a15, t15 = sd.scan(y, 15, want_tokens=True)
        sd7 = NativeSuffixDrafter(3, 64, 1 << 15); sd7.append(np.asarray(pr, np.int32))
        k7, m7, a7, t7 = sd7.scan(y, 7, want_tokens=True)
        for o in R:                                            # ricalcolo = traccia (verificato in sonda; riasserito)
            i = o["pos"]; lk = o["cand"]["lookup"]; tk = [] if lk is None else list(lk["tokens"])
            assert tk == [int(x) for x in t7[i, :k7[i]]] and int(o["acc"]["lookup"]) == int(a7[i])
        yp = voc.pieces(y); F = fences(yp); bnd = sorted(set(j + 1 for j, _ in F if j + 1 < n))
        cnt = np.zeros(n + 1, np.int64)                        # linee-fence completate prima della posizione i
        for j, _ in F: cnt[j + 1:] += 1
        lang = [info for _, info in F]
        Q.append(dict(key=key, idx=idx, req=rk[0], domain=r["domain"], split=r["split"], n=n, n_prompt=len(pr), y=y,
                      mtp_tok=mt, mtp_p=mp, mtp_acc=macc, k7=k7, m7=m7, a7=a7, tok0=t7[:, 0], k15=k15, m15=m15, a15=a15,
                      t15=t15, t7=t7, agree=(k7 > 0) & (t7[:, 0] == mt[:, 0]), bounds=bnd, in_code=(cnt[:n] % 2 == 1),
                      prompt_fence=FENCE.search(b"".join(voc.pieces(pr))) is not None, langs=lang, n_fence=len(F)))
    return Q


# ------------------------------------------------------------------ motore del round (regola del run file)
class Pol:
    """NativeDraftPolicy con log delle chiamate, per ricostruirne lo stato (oracolo per segmento)."""
    def __init__(self, S, log=None):
        self.S = S; self.p = NativeDraftPolicy(S); self.log = []
        for c in (log or []): self._do(*c)
    def _do(self, name, *a):
        self.log.append((name,) + a)
        if name == "robust": self.p.robust = a[0]; return None
        return getattr(self.p, name)(*a)
    def clone(self): return Pol(self.S, self.log)


def step(q, i, cfg, pol, rho):
    S, Sm, rule = cfg; n = q["n"]; pr = [float(x) for x in q["mtp_p"][i]]
    pol._do("robust", rule == "cost"); pol._do("set_context", q["n_prompt"] + i)
    if rule == "cost": T, _ = pol._do("mtp_chain_rows", pr, Sm)
    elif rule == "fixed": T = Sm
    else:
        T = 1
        while T < Sm and pr[T - 1] >= rule: T += 1
    Tm, look, m = T, False, 0
    if q["agree"][i]:
        k = min(int(q["k7"][i]), S - 1); m = int(q["m7"][i]); look, t = pol._do("choose", Tm, k, m)
        if look: T = t
    T = max(1, min(T, n - i)); a = int(min(q["a7"][i] if look else q["mtp_acc"][i], T - 1, n - i - 1))
    c = 1.0 + rho * (T - 1); ms = c * sim2.STEP_MS
    if look: pol._do("observe", True, T, a, m, ms)
    else:
        pol._do("observe", False, T, a, 0, ms)
        if rule == "cost": pol._do("observe_probs", pr, Tm - 1, a)
    return a, c, look


def run(q, rho, pick, pol, i=0, stop=None, hist=None):
    """pick(q,i,hist)->cfg. Ritorna (N, C, R, i_fine). hist: lista di (k>0, acc_lookup>=1) per lk_rate."""
    stop = q["n"] if stop is None else stop; N = C = R = 0
    hist = [] if hist is None else hist
    while i < stop and i < q["n"]:
        cfg = pick(q, i, hist); a, c, _ = step(q, i, cfg, pol, rho)
        hist.append((int(q["k7"][i]) > 0, int(q["a7"][i]) >= 1)); N += a + 1; C += c; R += 1; i += a + 1
    return N, C, R, i


def fixed_walk(q, cfg, rho): return run(q, rho, lambda *_: cfg, Pol(cfg[0]))[:3]


def seg_oracle(q, rho, sset):
    pol = Pol(8); hist = []; i = 0; N = C = R = 0; chosen = []
    edges = [b for b in q["bounds"]] + [q["n"]]
    for e in edges:
        if i >= e: continue
        best = None
        for cfg in sset:
            pc = pol.clone(); n_, c_, r_, _ = run(q, rho, lambda *_: cfg, pc, i, e, list(hist))
            if best is None or n_ / c_ > best[0] + 1e-15: best = (n_ / c_, cfg)
        n_, c_, r_, i = run(q, rho, lambda *_, c=best[1]: c, pol, i, e, hist)
        N += n_; C += c_; R += r_; chosen.append(best[1])
    return (N, C, R), chosen


def feats(q, i, hist, th_lk, th_p):
    h = [hi for (kk, hi) in hist[-N_LK:] if kk]
    rate = (sum(h) / len(h)) if h else 0.0
    return (int(q["in_code"][i]) << 3) | (int(q["prompt_fence"]) << 2) | (int(rate >= th_lk) << 1) | int(q["mtp_p"][i][0] >= th_p)


def cls_walk(q, rho, table, th):
    return run(q, rho, lambda qq, i, hist: table[feats(qq, i, hist, *th)], Pol(8))[:3]


def round_oracle(q, rho, tmax, lkmax, dp=True):
    n = q["n"]
    def opts(i):
        o = [(0, 1.0)]
        for T in range(2, min(tmax, n - i) + 1):
            if T <= 8: o.append((int(min(q["mtp_acc"][i], T - 1, n - i - 1)), 1 + rho * (T - 1)))
            if min(int(q["k15"][i]), lkmax) >= T - 1: o.append((int(min(q["a15"][i], T - 1, n - i - 1)), 1 + rho * (T - 1)))
        return o
    if dp:
        V = np.zeros(n + 1)
        for i in range(n - 1, -1, -1): V[i] = min(c + V[min(n, i + a + 1)] for a, c in opts(i))
        return n, float(V[0])
    i = 0; C = 0.0
    while i < n:
        a, c = max(opts(i), key=lambda o: (o[0] + 1) / o[1]); C += c; i += a + 1
    return n, C


# ------------------------------------------------------------------ smoke (nessuna metrica)
def smoke(out):
    assert sha(RUN) == RUN_SHA and sha(os.path.join(TR, "MANIFEST.sha256")) == MANIFEST_SHA
    rf = json.load(open(RUN)); assert len(GRID) == 168
    voc = Vocab(); S = {"run_sha256": RUN_SHA, "grid": len(GRID), "label": "smoke H-CA: solo lettura e forme, nessuna metrica", "files": {}}
    for key in FILES:
        Q = load(key, voc); C = collections.Counter(); lang = collections.Counter()
        for q in Q:
            C["requests"] += 1; C["positions"] += q["n"]; C["domain_" + q["domain"]] += 1
            C["prompt_fence"] += int(q["prompt_fence"]); C["fence_lines"] += q["n_fence"]
            C["requests_with_fence_in_y"] += int(q["n_fence"] > 0); C["segments"] += len(q["bounds"]) + 1
            C["k7_eq_min_k15_7"] += int(np.array_equal(q["k7"], np.minimum(q["k15"], 7)))
            C["t7_prefix_of_t15"] += int(all((q["t7"][i, :q["k7"][i]] == q["t15"][i, :q["k7"][i]]).all() for i in range(q["n"])))
            C["k15_gt7_positions"] += int((q["k15"] > 7).sum())
            for l in q["langs"]: lang[l or "<vuoto>"] += 1
        S["files"][key] = {"counts": C, "fence_info_strings": lang}
    p = Pol(8); p._do("set_context", 0); c = p.clone(); assert len(c.log) == len(p.log)
    S["native_policy_ok"] = True
    json.dump(S, open(out, "w"), indent=1, default=int); print(json.dumps(S, default=int)[:3000])


# ------------------------------------------------------------------ eval (NON eseguita in fase 1)
def tokps(rows): return sum(r[0] for r in rows) / sum(r[1] for r in rows)


def boot(rows_a, rows_b, B=2000, seed=0):
    rng = np.random.default_rng(seed); a = np.array(rows_a, float); b = np.array(rows_b, float); n = len(a); v = []
    for _ in range(B):
        ix = rng.integers(0, n, n); v.append((a[ix, 0].sum() / a[ix, 1].sum()) / (b[ix, 0].sum() / b[ix, 1].sum()) - 1)
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def fit_cls(Qtr, rho, A, base):
    best = None
    for th in [(a, b) for a in THETA_LK for b in THETA_P]:
        tab = [base] * 16
        score = lambda t: tokps([cls_walk(q, rho, t, th) for q in Qtr])
        cur = score(tab)
        for _ in range(2):
            for cell in range(16):
                for a in A:
                    if a == tab[cell]: continue
                    t2 = list(tab); t2[cell] = a; s2 = score(t2)
                    if s2 > cur + 1e-15: tab, cur = t2, s2
        if best is None or cur > best[0] + 1e-15: best = (cur, th, tab)
    return best[1], best[2]


def evaluate(outdir):
    assert sha(RUN) == RUN_SHA
    os.makedirs(outdir, exist_ok=False); voc = Vocab(); D = {k: load(k, voc) for k in FILES}
    res = {"run_sha256": RUN_SHA, "label": "PROXY CPU Qwen3.5-2B, tok/s STIMATI s(T)=1+rho(T-1), draft a costo zero", "scen": {}}
    for sc, rho in RHO.items():
        W = {k: [[fixed_walk(q, g, rho) for g in GRID] for q in Q] for k, Q in D.items()}
        tune = D["tune"]; Wt = W["tune"]
        g1 = max(range(len(GRID)), key=lambda g: (tokps([w[g] for w in Wt]), -g)); cfg1 = GRID[g1]
        r0 = [g for g in GRID if g[:2] == cfg1[:2] and g[2] != "cost"] if cfg1[2] != "cost" else []
        out = {"arm1": list(cfg1), "R0_only_set": r0, "dom": {}}
        seg = {k: [seg_oracle(q, rho, GRID) for q in Q] for k, Q in D.items()}
        seg0 = {k: [seg_oracle(q, rho, r0)[0] if r0 else None for q in Q] for k, Q in D.items()}
        cnt = collections.Counter(c for _, ch in seg["tune"] for c in ch)
        A = sorted(cnt, key=lambda c: (-cnt[c], GRID.index(c)))[:MAXA]
        if cfg1 not in A: A.append(cfg1)
        cv = [None] * len(tune)
        for f in range(NFOLD):
            tr = [q for q in tune if q["idx"] % NFOLD != f]; th, tab = fit_cls(tr, rho, A, cfg1)
            for j, q in enumerate(tune):
                if q["idx"] % NFOLD == f: cv[j] = cls_walk(q, rho, tab, th)
        th, tab = fit_cls(tune, rho, A, cfg1)
        out.update(A=A, theta=th, table=tab)
        for k, Q in D.items():
            for d in DOMAINS:
                ix = [j for j, q in enumerate(Q) if q["domain"] == d]
                if not ix: continue
                a1 = [W[k][j][g1] for j in ix]
                a2 = [max(W[k][j], key=lambda w: w[0] / w[1]) for j in ix]
                a3 = [seg[k][j][0] for j in ix]
                cl = [cv[j] for j in ix] if k == "tune" else [cls_walk(Q[j], rho, tab, th) for j in ix]
                cl_in = [cls_walk(Q[j], rho, tab, th) for j in ix]
                ro = {lab: [round_oracle(Q[j], rho, tm, lm) for j in ix] for lab, tm, lm in (("R01", 8, 7), ("P", 12, 11), ("X", 16, 15))}
                ror = [round_oracle(Q[j], rho, 8, 7, dp=False) for j in ix]
                e = {"tokps": {"1": tokps(a1), "2": tokps(a2), "3": tokps(a3), "cls": tokps(cl), "cls_insample": tokps(cl_in),
                               **{"round_" + l: tokps(v) for l, v in ro.items()}, "round_greedy_R01": tokps(ror)},
                     "AL": {"1": sum(r[0] for r in a1) / sum(r[2] for r in a1), "2": sum(r[0] for r in a2) / sum(r[2] for r in a2),
                            "3": sum(r[0] for r in a3) / sum(r[2] for r in a3), "cls": sum(r[0] for r in cl) / sum(r[2] for r in cl)},
                     "ci95": {"2_vs_1": boot(a2, a1), "3_vs_1": boot(a3, a1), "cls_vs_1": boot(cl, a1)}}
                if seg0[k][0] is not None: e["tokps"]["3_R0only"] = tokps([seg0[k][j] for j in ix])
                g = e["tokps"]["2"] / e["tokps"]["1"] - 1; e["gain_2_over_1"] = g
                e["capture"] = (e["tokps"]["cls"] - e["tokps"]["1"]) / (e["tokps"]["2"] - e["tokps"]["1"]) if g > 0 else None
                out["dom"]["%s/%s" % (k, d)] = e
        res["scen"][sc] = out
    T = {sc: {d: res["scen"][sc]["dom"]["tune/" + d] for d in DOMAINS} for sc in RHO}
    falls = any(all(T[sc][d]["gain_2_over_1"] < 0.03 for d in DOMAINS) for sc in RHO)
    nogo = any(all((T[sc][d]["capture"] or 0) < 0.5 for d in DOMAINS if T[sc][d]["gain_2_over_1"] >= 0.03) for sc in RHO)
    res["verdict"] = {"H-CA_scende": falls, "classificatore_NO-GO": nogo, "base": "tune, stime puntuali, switch R0 U R1"}
    json.dump(res, open(os.path.join(outdir, "hca_results.json"), "x"), indent=1, default=str)


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    if sys.argv[1] == "smoke": smoke(sys.argv[2])
    elif sys.argv[1] == "eval":
        assert "--authorized" in sys.argv, "eval richiede l'autorizzazione dell'utente (--authorized)"
        evaluate(sys.argv[2])
    else: sys.exit(2)
