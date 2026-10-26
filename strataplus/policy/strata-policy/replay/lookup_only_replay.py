"""Pre-registered lookup-only replay (Strata Lead 07:06 CET), fixed in replay/run_lookup_only_replay.json (sha256 584ae02f...,
read-only, written before computing).  AL only, DESCRIPTIVE.  Holdout v1.1, arms dmax 7/12/16.  usage: script OUTDIR"""
import json, os, sys, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strata_sim.postprocess import load_tf
from strata_sim.native import NativeSuffixDrafter

OUTD = sys.argv[1]; os.makedirs(OUTD, exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
RUNF = os.path.join(HERE, "run_lookup_only_replay.json")
assert sha(RUNF) == "584ae02f6a60ed89f6a7cf7268106ebbc9834452f36d0fb46fb2f77eb8e7a40b"
RUN = json.load(open(RUNF))
TR = "/workspace/strata-plus/traces/v1.1"
FILES = {d: os.path.join(TR, "holdout_%s_tf_d7.jsonl" % d) for d in ("code", "chat", "edit")}
for d, p in FILES.items():
    assert sha(p) == RUN["inputs_sha256"][os.path.basename(p)], p
for k in ("strata_sim/native.py", "strata_sim/postprocess.py", "native/libstrata_spec_capi.so"):
    assert sha(os.path.join(HERE, k)) == RUN["inputs_sha256"][k], k
ARMS = (7, 12, 16)
B, SEED = 2000, 0
rng = np.random.default_rng(SEED)


def prompts(path):
    P = {}
    for l in open(path):
        o = json.loads(l)
        if o.get("type") == "request" and o.get("rep", 0) == 0:
            P[o["req_id"]] = o["prompt_ids"]
    return P


def walk(n, k, acc, dmax):
    """lookup-only: round at p proposes cand[:dmax] (k=0 -> 1 token, no draft); a = min(lcp, n-p-1); p += a+1."""
    p = 0; R = 0; RC = 0; hist = np.zeros(dmax + 1, np.int64); h0 = 0
    while p < n:
        if k[p] > 0:
            a = min(int(acc[p]), n - p - 1); RC += 1; hist[a] += 1
        else:
            a = 0; h0 += 1
        R += 1; p += a + 1
    return R, RC, hist, h0


OUT = {"label": "replay lookup-only PRE-REGISTRATO, holdout v1.1, solo AL, descrittivo; proxy CPU 2B, non AMD",
       "run_file_sha256": sha(RUNF), "script_sha256": sha(os.path.abspath(__file__)),
       "files_sha256": {d: sha(p) for d, p in FILES.items()}, "arms_dmax": ARMS, "B": B, "seed": SEED, "results": {}}
for dom, path in FILES.items():
    reqs = load_tf(path); P = prompts(path)
    per = {d: [] for d in ARMS}; chk = dict(positions=0, k_mismatch=0, tok_mismatch=0, acc_mismatch=0)
    for q in reqs:
        y = q["y"]; n = q["n"]
        for d in ARMS:
            sd = NativeSuffixDrafter(3, 64, 1 << 15); sd.append(np.asarray(P[q["req"]], np.int32))
            k, m, acc, tok = sd.scan(y, d, want_tokens=True)
            if d == 7:
                chk["positions"] += n
                chk["k_mismatch"] += int(np.sum(k != q["lk_k"]))
                chk["acc_mismatch"] += int(np.sum(acc != q["lk_acc"]))
                for i in range(n):
                    if not np.array_equal(tok[i, :k[i]], q["lk_tok"][i, :k[i]]):
                        chk["tok_mismatch"] += 1
            R, RC, hist, h0 = walk(n, k, acc, d)
            per[d].append(dict(req=q["req"], n=n, R=R, RC=RC, hist=hist, h0=h0))
    assert chk["k_mismatch"] == chk["tok_mismatch"] == chk["acc_mismatch"] == 0, ("STOP: dmax7 vs traces", dom, chk)
    res = dict(n_req=len(reqs), check_dmax7_vs_traces=chk, arms={})
    S = rng.integers(0, len(reqs), (B, len(reqs)))
    for d in ARMS:
        N = np.array([r["n"] for r in per[d]], float); R = np.array([r["R"] for r in per[d]], float)
        RC = np.array([r["RC"] for r in per[d]], float)
        al = N.sum() / R.sum(); alb = N[S].sum(1) / R[S].sum(1)
        sh = RC.sum() / R.sum(); shb = RC[S].sum(1) / R[S].sum(1)
        H = np.sum([r["hist"] for r in per[d]], 0); H0 = int(sum(r["h0"] for r in per[d]))
        res["arms"][str(d)] = dict(
            tokens=int(N.sum()), rounds=int(R.sum()), AL=float(al), AL_ci95=[float(np.percentile(alb, 2.5)), float(np.percentile(alb, 97.5))],
            share_rounds_with_candidate=float(sh), share_ci95=[float(np.percentile(shb, 2.5)), float(np.percentile(shb, 97.5))],
            hist_rounds_no_candidate=H0, hist_acc_rounds_with_candidate={str(a): int(c) for a, c in enumerate(H)},
            per_request=[dict(req=r["req"], n=r["n"], rounds=r["R"], rounds_with_candidate=r["RC"]) for r in per[d]])
        assert int(N.sum()) == int(sum(r["n"] for r in per[d])) and H0 + int(H.sum()) == int(R.sum())
    OUT["results"][dom] = res
    print(dom, "n_req", len(reqs), "check", chk, {d: (round(v["AL"], 4), [round(x, 4) for x in v["AL_ci95"]], round(v["share_rounds_with_candidate"], 4)) for d, v in res["arms"].items()}, flush=True)
json.dump(OUT, open(os.path.join(OUTD, "lookup_only_replay.json"), "w"), indent=1)
