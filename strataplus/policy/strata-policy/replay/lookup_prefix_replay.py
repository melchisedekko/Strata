"""Lookup-only replay vs Bench live run holdout_lookup_v12 (Strata Lead 07:55 CET). proxy CPU, AL, DESCRITTIVO.
Fixed in replay/run_lookup_prefix_replay.json (sha256 16fb6a43..., read-only, written before reading live data).
Replay logic = replay/lookup_only_replay.py (2bd35901...).  usage: script OUTDIR"""
import json, os, sys, hashlib, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strata_sim.postprocess import load_tf
from strata_sim.native import NativeSuffixDrafter

OUTD = sys.argv[1]; os.makedirs(OUTD, exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
RUNF = os.path.join(HERE, "run_lookup_prefix_replay.json")
assert sha(RUNF) == "16fb6a43e5e546b0e4b779e16ea28bf9f62b4dcec7395d19fd4e9b1f182a9ed2"
RUN = json.load(open(RUNF))
for k, v in RUN["inputs_sha256"].items():
    p = k.split(" ")[-1]
    p = p if p.startswith("/") else os.path.join(os.path.dirname(HERE), p)
    assert sha(p) == v, p
LV = "/workspace/strata-plus/traces/holdout_lookup_v12"
TR = "/workspace/strata-plus/traces/v1.1"
FILES = {d: os.path.join(TR, "holdout_%s_tf_d7.jsonl" % d) for d in ("code", "chat", "edit")}
ARMS = (7, 12, 16)
DOMS = ("code", "chat", "edit")
SUMM = json.load(open(os.path.join(LV, "holdout_lookup_v12_summary.json")))
REF = {}
for l in open(os.path.join(LV, "ref_holdout_tf.tsv")):
    k, v = l.rstrip("\n").split("\t"); REF[k] = [int(x) for x in v.split(",") if x]


def prompts(path):
    P = {}
    for l in open(path):
        o = json.loads(l)
        if o.get("type") == "request" and o.get("rep", 0) == 0:
            P[o["req_id"]] = o["prompt_ids"]
    return P


def walk(n, k, acc):
    """lookup-only replay (lookup_only_replay.py): returns per-round (pos, a, had_candidate)."""
    p = 0; out = []
    while p < n:
        a = min(int(acc[p]), n - p - 1) if k[p] > 0 else 0
        out.append((p, a, bool(k[p] > 0))); p += a + 1
    return out


# ---- replay on the reference
TF = {}; REP = {d: {} for d in ARMS}; SCAN = {d: {} for d in ARMS}
for dom, path in FILES.items():
    P = prompts(path)
    for q in load_tf(path):
        TF[q["req"]] = dict(dom=dom, y=[int(t) for t in q["y"]], prompt=P[q["req"]])
        for d in ARMS:
            sd = NativeSuffixDrafter(3, 64, 1 << 15); sd.append(np.asarray(P[q["req"]], np.int32))
            k, m, acc, tok = sd.scan(q["y"], d, want_tokens=True)
            SCAN[d][q["req"]] = (k, acc, tok)
            REP[d][q["req"]] = walk(q["n"], k, acc)

# ---- live
LIVE = {d: {} for d in ARMS}; anomalies = []
for d in ARMS:
    reqs = {}; rounds = collections.defaultdict(list); ends = {}
    for l in open(os.path.join(LV, "holdout_lookup_v12_n%d.jsonl" % d)):
        j = json.loads(l)
        if j["type"] == "request": reqs[j["req_id"]] = j
        elif j["type"] == "round": rounds[j["req_id"]].append(j)
        elif j["type"] == "request_end": ends[j["req_id"]] = j
    for r, j in reqs.items():
        rs = sorted(rounds[r], key=lambda x: x["r"])
        bad = [x["r"] for x in rs if x["committed"] != x["accepted"] + 1]
        assert not bad, ("STOP: committed != accepted+1", d, r, bad[:5])
        LIVE[d][r] = dict(req=j, rounds=rs, out=ends[r]["output_ids"])

text_check = dict(same_req_ids=all(set(LIVE[d]) == set(TF) for d in ARMS), n_req=len(TF),
                  ref_tsv_equals_replay_y=all(REF[r] == TF[r]["y"] for r in TF),
                  live_prompt_equals_replay_prompt={d: sum(LIVE[d][r]["req"]["prompt_ids"] == TF[r]["prompt"] for r in TF) for d in ARMS},
                  live_ref_tokens_equals_ref={d: sum(LIVE[d][r]["req"]["ref_tokens"] == TF[r]["y"] for r in TF) for d in ARMS},
                  live_len_equals_ref_len={d: sum(len(LIVE[d][r]["out"]) == len(TF[r]["y"]) for r in TF) for d in ARMS})


def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y: break
        n += 1
    return n


def al(rows):  # rows: list of committed counts
    return (sum(rows) / len(rows)) if rows else None


res = {}; per_req = []
for d in ARMS:
    S = SUMM["arms"]["holdout_lookup_v12_n%d" % d]
    for r in TF:
        Lq = LIVE[d][r]; y = TF[r]["y"]; out = Lq["out"]
        dv_calc = None if lcp(out, y) == len(out) == len(y) else lcp(out, y)
        dv = Lq["req"]["first_divergence_pos"]
        assert dv == dv_calc, ("STOP: first_divergence_pos", d, r, dv, dv_calc)
        lim = dv if dv is not None else 10 ** 9
        lv_full = [x["committed"] for x in Lq["rounds"]]
        lv_pre = [x["committed"] for x in Lq["rounds"] if x["pos"] + x["committed"] <= lim]
        rp = REP[d][r]
        rp_full = [a + 1 for (p, a, c) in rp]
        rp_pre = [a + 1 for (p, a, c) in rp if p + a + 1 <= lim]
        # round-by-round on the common prefix: same pos -> same proposal?
        k, acc, tok = SCAN[d][r]
        same_pos = prop_mismatch = acc_mismatch = 0
        for x in Lq["rounds"]:
            p = x["pos"]
            if p + x["committed"] > lim or p >= len(y):
                continue
            same_pos += 1
            lk = x["cand"]["lookup"]["tokens"][:d]
            rk = [int(t) for t in tok[p, :k[p]]]
            if lk != rk: prop_mismatch += 1
            if x["accepted"] != min(int(acc[p]) if k[p] > 0 else 0, len(y) - p - 1): acc_mismatch += 1
        per_req.append(dict(arm=d, req=r, dom=TF[r]["dom"], equal_ref=dv is None, first_div=dv, n_ref=len(y), n_live=len(out),
                            live_rounds=len(lv_full), live_tok=sum(lv_full), live_acc=sum(lv_full) - len(lv_full),
                            rep_rounds=len(rp_full), rep_tok=sum(rp_full), rep_acc=sum(rp_full) - len(rp_full),
                            live_pre_rounds=len(lv_pre), live_pre_tok=sum(lv_pre), rep_pre_rounds=len(rp_pre), rep_pre_tok=sum(rp_pre),
                            prefix_rounds_checked=same_pos, prefix_proposal_mismatch=prop_mismatch, prefix_accept_mismatch=acc_mismatch,
                            live_rounds_with_cand=sum(1 for x in Lq["rounds"] if x["cand"]["lookup"]["tokens"]),
                            rep_rounds_with_cand=sum(1 for (p, a, c) in rp if c)))
    for dom in DOMS:
        rows = [x for x in per_req if x["arm"] == d and x["dom"] == dom]
        def agg(sub, kt, kr):
            t = sum(x[kt] for x in sub); n = sum(x[kr] for x in sub)
            return (t / n if n else None, t, n)
        o = {}
        for name, sub in (("all", rows), ("equal_ref", [x for x in rows if x["equal_ref"]]), ("divergent", [x for x in rows if not x["equal_ref"]])):
            lf = agg(sub, "live_tok", "live_rounds"); rf = agg(sub, "rep_tok", "rep_rounds")
            lp = agg(sub, "live_pre_tok", "live_pre_rounds"); rpp = agg(sub, "rep_pre_tok", "rep_pre_rounds")
            pct = lambda a, b: (100 * (a - b) / b) if (a is not None and b) else None
            o[name] = dict(requests=len(sub), live_full=lf, replay_full=rf, delta_full_pct=pct(lf[0], rf[0]),
                           live_prefix=lp, replay_prefix=rpp, delta_prefix_pct=pct(lp[0], rpp[0]),
                           prefix_rounds_checked=sum(x["prefix_rounds_checked"] for x in sub),
                           prefix_proposal_mismatch=sum(x["prefix_proposal_mismatch"] for x in sub),
                           prefix_accept_mismatch=sum(x["prefix_accept_mismatch"] for x in sub))
        s = S["summary"][dom]
        o["bench_summary"] = s
        o["check_live_full_vs_bench"] = abs(round(o["all"]["live_full"][0], 4) - s["AL_full"]) < 1e-9 and o["all"]["live_full"][2] == s["rounds_full"]
        o["check_live_prefix_vs_bench"] = abs(round(o["all"]["live_prefix"][0], 4) - s["AL_pre_div"]) < 1e-9 and o["all"]["live_prefix"][2] == s["rounds_pre_div"]
        o["check_replay_full_vs_lookup_only_replay"] = None
        res.setdefault(dom, {})[str(d)] = o

PREV = json.load(open(os.path.join(HERE, "results/v2/lookup_only_replay/lookup_only_replay.json")))
for dom in DOMS:
    for d in ARMS:
        o = res[dom][str(d)]
        o["check_replay_full_vs_lookup_only_replay"] = (o["all"]["replay_full"][0] == PREV["results"][dom]["arms"][str(d)]["AL"])
        assert o["check_replay_full_vs_lookup_only_replay"], (dom, d)
OUT = dict(label="proxy CPU, AL, descrittivo", run_file_sha256=sha(RUNF), script_sha256=sha(os.path.abspath(__file__)),
           text_check=text_check, bench_validity_note=SUMM.get("validity_note"), bench_outputs_identical_across_arms=SUMM.get("outputs_identical_across_arms"),
           results=res, per_request=per_req)
json.dump(OUT, open(os.path.join(OUTD, "lookup_prefix_replay.json"), "w"), indent=1)
print("text_check", json.dumps(text_check))
for dom in DOMS:
    for d in ARMS:
        o = res[dom][str(d)]
        print(dom, d, {n: (o[n]["requests"], round(o[n]["live_full"][0], 4) if o[n]["live_full"][0] else None, round(o[n]["replay_full"][0], 4) if o[n]["replay_full"][0] else None,
                           round(o[n]["live_prefix"][0], 4) if o[n]["live_prefix"][0] else None, round(o[n]["replay_prefix"][0], 4) if o[n]["replay_prefix"][0] else None,
                           o[n]["prefix_rounds_checked"], o[n]["prefix_proposal_mismatch"], o[n]["prefix_accept_mismatch"]) for n in ("all", "equal_ref", "divergent")},
              "checks", o["check_live_full_vs_bench"], o["check_live_prefix_vs_bench"], flush=True)
