"""Diagnosi aggiuntiva (descrittiva) per results/v2/lookup_prefix_replay: (1) edit senza la richiesta con la differenza
maggiore; (2) round live in cui committed supera i token di output (EOS dentro il draft). Legge solo il json dei risultati
e le tracce live verificate. usage: script OUTDIR"""
import json, os, sys, hashlib
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
HERE = os.path.dirname(os.path.abspath(__file__)); OUTD = sys.argv[1]
RJ = os.path.join(OUTD, "lookup_prefix_replay.json"); o = json.load(open(RJ))
assert o["run_file_sha256"] == "16fb6a43e5e546b0e4b779e16ea28bf9f62b4dcec7395d19fd4e9b1f182a9ed2"
LV = "/workspace/strata-plus/traces/holdout_lookup_v12"
EXP = {7: "35f881debbea54b1dfa4f6110385f00ecc6dc72fe17835af22a7a92aed3c6b69", 12: "58c2d5d431c57a92ec8253266f59a67adeb7cc83c62ff6344f5675147052c94a",
       16: "93c9ae1f0f81e9c3facfeedc70421a4f27fbe2e9d40a843c34dd866535655fd9"}
P = o["per_request"]; D = {"results_json_sha256": sha(RJ), "edit_without_max_diff": {}, "live_committed_beyond_output": []}
for d in (7, 12, 16):
    e = [x for x in P if x["arm"] == d and x["dom"] == "edit"]
    top = max(e, key=lambda x: abs(x["live_acc"] - x["rep_acc"]))
    s = [x for x in e if x["req"] != top["req"]]
    lt, lr = sum(x["live_tok"] for x in s), sum(x["live_rounds"] for x in s)
    rt, rr = sum(x["rep_tok"] for x in s), sum(x["rep_rounds"] for x in s)
    D["edit_without_max_diff"][str(d)] = dict(excluded=top["req"], live=[lt / lr, lt, lr], replay=[rt / rr, rt, rr], delta_pct=100 * (lt / lr - rt / rr) / (rt / rr),
                                              excluded_live_rounds_tok_acc=[top["live_rounds"], top["live_tok"], top["live_acc"]],
                                              excluded_rep_rounds_tok_acc=[top["rep_rounds"], top["rep_tok"], top["rep_acc"]], excluded_first_div=top["first_div"])
    p = os.path.join(LV, "holdout_lookup_v12_n%d.jsonl" % d); assert sha(p) == EXP[d]
    rounds = {}; outs = {}
    for l in open(p):
        j = json.loads(l)
        if j["type"] == "round": rounds.setdefault(j["req_id"], []).append(j)
        elif j["type"] == "request_end": outs[j["req_id"]] = j["output_ids"]
    for r, rs in rounds.items():
        n = len(outs[r])
        for x in rs:
            if x["pos"] + x["committed"] > n:
                D["live_committed_beyond_output"].append(dict(arm=d, req=r, pos=x["pos"], k_proposed=x["k_proposed"], accepted=x["accepted"], committed=x["committed"],
                                                               output_len=n, target_tokens=x["target_tokens"], lookup_tokens=x["cand"]["lookup"]["tokens"]))
json.dump(D, open(os.path.join(OUTD, "lookup_prefix_diag.json"), "w"), indent=1)
print(json.dumps(D, indent=1))
