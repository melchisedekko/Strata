"""H-CA fase 1: SONDA DI COPERTURA sui record delle tracce v1.1 (tune tf_d7_p30 + holdout_{code,chat,edit}_tf_d7).
Solo forma e completezza dei campi, nessuna metrica di risultato (niente AL, tok/s, accettanze aggregate).
Controlla: header (data_kind, dmax, lookup_max_match, split), una riga round per ogni pos 0..n-1, cand.mtp tokens/probs/ent
a lunghezza dmax e finiti, cand.lookup (null o tokens<=dmax, match), campi chain/pool, acc.{mtp,lookup}, committed, EOS
(EOG dentro y prima della fine, somma committed vs output_tokens), coerenza del lookup ricalcolato con il SuffixDrafter
nativo (3, 64) da prompt_ids + y contro cand.lookup della traccia.  usage: hca_coverage_probe.py OUT.json"""
import json, os, sys, hashlib, math, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strata_sim.native import NativeSuffixDrafter

TR = "/workspace/strata-plus/traces/v1.1"
FILES = {"tune": "tf_d7_p30.jsonl", "holdout_code": "holdout_code_tf_d7.jsonl",
         "holdout_chat": "holdout_chat_tf_d7.jsonl", "holdout_edit": "holdout_edit_tf_d7.jsonl"}
EXP = {"tune": "87efe507324b2a79b89c21a6736f1478094bf53385d9471694dc71b291d9abfa",
       "holdout_code": "a9e247b2fd9a0da14517459f028d2b9e85195955895855459c3c924f0e37f603",
       "holdout_chat": "b5380c42b9155571054958f00cb501ca7a309feaf8e9cc058f54bd00692b4588",
       "holdout_edit": "d9a48386945b1131766cb8b38a1572bc2d3992d8b5bd8291ecbe85c79f3e94ef"}
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
unl = lambda v: v[2] if isinstance(v, list) and len(v) == 3 and v[0] == "list" else v   # ["list", n, [...]] wrapper
OUT = {"label": "sonda di copertura H-CA, solo forma dei record, nessuna metrica", "files": {}}
for key, fn in FILES.items():
    p = os.path.join(TR, fn); h = sha(p); assert h == EXP[key], key
    req, rounds, ends = {}, collections.defaultdict(list), {}
    for l in open(p):
        o = json.loads(l); t = o.get("type")
        if t == "request": req[(o["req_id"], o.get("rep", 0))] = o
        elif t == "round": rounds[(o["req_id"], o.get("rep", 0))].append(o)
        elif t == "request_end": ends[(o["req_id"], o.get("rep", 0))] = o
    C = collections.Counter(); hdr = collections.defaultdict(collections.Counter); last_tok = collections.Counter()
    lens_short = []; lk_mism = collections.Counter(); cand_keys = collections.Counter(); acc_keys = collections.Counter()
    for rk, q in req.items():
        for f in ("data_kind", "dmax", "lookup_max_match", "split", "run_id", "domain", "sampling", "greedy_equal_ref"):
            hdr[f][str(q.get(f))] += 1
        C["requests"] += 1
        n = int(q["output_tokens"]); pr = unl(q.get("prompt_ids"))
        C["prompt_ids_ok"] += int(isinstance(pr, list) and len(pr) == q.get("prompt_tokens"))
        e = ends.get(rk); y = unl(e["output_ids"]) if e else None
        C["output_ids_ok"] += int(y is not None and len(y) == n)
        ref = unl(q.get("ref_tokens")); C["ref_eq_output"] += int(ref == y)
        R = sorted(rounds.get(rk, []), key=lambda o: o["pos"])
        C["pos_complete"] += int([o["pos"] for o in R] == list(range(n)))
        C["committed_sum_eq_n"] += int(sum(o["committed"] for o in R) == n)
        C["committed_all_1"] += int(all(o["committed"] == 1 and o["T"] == 1 for o in R))
        if n < 128: lens_short.append(n); last_tok[y[-1]] += 1
        for o in R:
            C["rounds"] += 1
            cm = o["cand"].get("mtp"); cand_keys[tuple(sorted(o["cand"].keys()))] += 1; acc_keys[tuple(sorted(o["acc"].keys()))] += 1
            if cm is None: C["mtp_null"] += 1; continue
            for f in ("tokens", "probs", "ent", "probs_sampler"):
                v = cm.get(f)
                C["mtp_%s_len%s" % (f, len(v) if v is not None else "None")] += 1
                if v is not None:
                    C["mtp_%s_nonfinite" % f] += sum(1 for x in v if x is None or not math.isfinite(float(x)))
            pv = [x for x in cm["probs"] if x is not None]
            C["mtp_probs_out_of_0_1"] += sum(1 for x in pv if not (0.0 <= x <= 1.0))
            if o["pos"] < n - 1:   # target_tokens/committed: the teacher-forced token is y[pos]
                C["target_eq_y"] += int(o["target_tokens"] == [y[o["pos"]]])
            lk = o["cand"].get("lookup")
            if lk is None: C["lookup_null"] += 1
            else:
                C["lookup_present"] += 1; C["lookup_tokens_maxlen_%d" % len(lk["tokens"])] += 0
                C["lookup_len_gt_dmax"] += int(len(lk["tokens"]) > 7)
        # recompute lookup with the production SuffixDrafter (min_match 3, max_match 64, as generate.cpp L11177/L16400s)
        sd = NativeSuffixDrafter(3, 64, 1 << 15); sd.append(np.asarray(pr, np.int32))
        k7, m7, a7, tok7 = sd.scan(y, 7, want_tokens=True)
        for o in R:
            i = o["pos"]; lk = o["cand"].get("lookup")
            tk = [] if lk is None else list(lk["tokens"]); mt = 0 if lk is None else int(lk.get("match", -1))
            lk_mism["k"] += int(len(tk) != int(k7[i])); lk_mism["tokens"] += int(tk != [int(x) for x in tok7[i, :k7[i]]])
            if lk is not None: lk_mism["match"] += int(mt != int(m7[i]))
            lk_mism["acc"] += int(int(o["acc"]["lookup"]) != int(a7[i]))
        # EOS: does an end token appear inside y before its last position?  (end ids learnt from requests ending before -n)
    OUT["files"][key] = dict(path=p, sha256=h, header=hdr, counts=C, n_short=len(lens_short), last_token_of_short=last_tok,
                             cand_keys={"|".join(k): v for k, v in cand_keys.items()}, acc_keys={"|".join(k): v for k, v in acc_keys.items()},
                             lookup_recompute_mismatch=lk_mism, _y={str(k): unl(ends[k]["output_ids"]) for k in req})
# EOS scan across all files with the end ids observed as last token of short outputs
eog = set()
for v in OUT["files"].values(): eog |= set(int(t) for t in v["last_token_of_short"])
for key, v in OUT["files"].items():
    ys = v.pop("_y"); inside = []
    for rk, y in ys.items():
        for j, t in enumerate(y[:-1]):
            if t in eog: inside.append((rk, j, t, len(y)))
    v["eog_ids_observed"] = sorted(eog); v["eog_inside_before_end"] = inside
    v["outputs_ending_with_eog"] = sum(1 for y in ys.values() if y and y[-1] in eog)
json.dump(OUT, open(sys.argv[1], "w"), indent=1, default=lambda x: dict(x) if isinstance(x, collections.Counter) else str(x))
for key, v in OUT["files"].items():
    print(key, json.dumps({k: v[k] for k in ("header", "counts", "n_short", "last_token_of_short", "cand_keys", "acc_keys",
                                            "lookup_recompute_mismatch", "outputs_ending_with_eog", "eog_inside_before_end")}, default=dict))
