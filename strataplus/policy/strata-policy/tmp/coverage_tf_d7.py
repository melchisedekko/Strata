"""Ispezione di copertura (nessun AL): proposte MTP (tokens, probs) e lookup (tokens, match) per round/posizione; EOS."""
import json, sys, collections, hashlib
f = sys.argv[1]
hdr = None; reqs = {}; ends = {}; R = collections.defaultdict(list); first = {}
for i, l in enumerate(open(f)):
    j = json.loads(l); t = j["type"]
    first.setdefault(t, (i + 1, sorted(j)))
    if t == "header": hdr = j
    elif t == "request": reqs[(j["req_id"], j.get("rep", 0))] = j
    elif t == "request_end": ends[(j["req_id"], j.get("rep", 0))] = j
    elif t == "round": R[(j["req_id"], j.get("rep", 0))].append((i + 1, j))
print("header:", json.dumps(hdr)[:1500])
for t, (ln, ks) in first.items(): print("first", t, "line", ln, ks)
print("types", {t: v for t, v in collections.Counter([k for k in first]).items()}, "requests", len(reqs), "ends", len(ends), "rounds", sum(len(v) for v in R.values()))
print("reps", collections.Counter(k[1] for k in reqs))
dom = collections.defaultdict(collections.Counter); holes = collections.defaultdict(list)
for k, rs in R.items():
    d = rs[0][1]["domain"]; out = ends[k]["output_ids"]; n = len(out)
    poss = [j["pos"] for _, j in rs]
    C = dom[d]; C["requests"] += 1; C["rounds"] += len(rs); C["positions_out"] += n
    C["pos_contiguous_0..n-1"] += (poss == list(range(n)))
    C["sum_committed_gt_output"] += sum(j["committed"] for _, j in rs) > n
    C["T>1"] += sum(j["T"] > 1 for _, j in rs)
    for ln, j in rs:
        m = j["cand"]["mtp"]; lk = j["cand"]["lookup"]
        nt = len(m["tokens"]); np_ = len(m["probs"])
        C["mtp_len_%d" % nt] += 1
        C["mtp_tokens>=3"] += nt >= 3
        C["mtp_probs==tokens"] += np_ == nt
        C["mtp_ok(>=3 & probs)"] += (nt >= 3 and np_ >= 3)
        C["lookup_len_%d" % len(lk["tokens"])] += 1
        C["lookup_has_match_field"] += "match" in lk
        C["lookup_nonempty"] += len(lk["tokens"]) > 0
        C["lookup_nonempty_and_match>=3"] += len(lk["tokens"]) > 0 and lk["match"] >= 3
        C["lookup_empty_but_match>0"] += len(lk["tokens"]) == 0 and lk["match"] > 0
        C["source_" + j["source"]] += 1
        C["k_cap_%s" % j["k_cap"]] += 1
        if j["committed"] > 1 or j["pos"] >= n: C["round_committed>1_or_pos>=n"] += 1
        if not (nt >= 3 and np_ >= 3):
            holes[d].append((k[0], j["pos"], n, nt, np_, ln))
        if out[j["pos"]:j["pos"]+1] and j["target_tokens"][:1] != out[j["pos"]:j["pos"]+1]: C["target0!=output[pos]"] += 1
    # tokens after EOS in output?
    C["eos_not_last"] += any(t == 248046 for t in out[:-1])
for d, C in dom.items(): print(d, dict(sorted(C.items())))
for d, h in holes.items():
    print("HOLES", d, len(h), "remaining-tokens profile (n-pos):", collections.Counter(min(x[2] - x[1], 9) for x in h))
    print("  examples", h[:8])
json.dump({d: dict(C) for d, C in dom.items()} | {"_holes": {d: h for d, h in holes.items()}}, open(sys.argv[2], "w"))
