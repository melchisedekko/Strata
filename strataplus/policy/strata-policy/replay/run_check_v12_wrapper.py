"""Minimal wrapper: runs the FROZEN replay/holdout_v11_speccost_vs_default.py (sha256 6809946d…, not modified) on
check_v12 instead of holdout v1.1.  The frozen script hard-codes the holdout paths (HO = holdout_{d}_tf_d7.jsonl) and
calls strata_sim.postprocess.load_tf(path); this wrapper replaces load_tf, before running the script with runpy, by a
function that loads check_v12_tf_d7.jsonl once and returns the requests of domain d for the path holdout_{d}_tf_d7.jsonl.
Step 1 (schema gate) reads ONLY metadata: request records' scalar fields (schema, data_kind, dmax, domain, split, flags…)
and the KEY NAMES of round records plus draft_p_min / n_max / n_min; no metric (tokens, probs, stats) is read.  If the
schema differs from v1.1 the wrapper STOPS (exit 3) and prints the difference; nothing is adapted.
usage: nice -n 19 python3 run_check_v12_wrapper.py OUTDIR"""
import json, os, sys, hashlib, runpy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
CK = "/workspace/strata-plus/traces/check_v12/check_v12_tf_d7.jsonl"
REF = "/workspace/strata-plus/traces/v1.1/holdout_code_tf_d7.jsonl"
FROZEN = os.path.join(HERE, "holdout_v11_speccost_vs_default.py")
FROZEN_SHA = "6809946d6cba46296ba819b047b2e8fae08c307ff38392c6e4c1e9f2a27b1f48"
OUTD = sys.argv[1]; os.makedirs(OUTD, exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
META = ("schema", "data_kind", "dmax", "domain", "split", "sampling", "engine", "pos_semantics", "lookup_max_match", "rep")
SKIP = {"prompt_ids", "ref_tokens", "output_ids", "stats", "cand", "target_tokens"}


def schema(path, max_rounds=2000):
    req_keys, rnd_keys, vals, doms, extra = set(), set(), {k: set() for k in META}, {}, {}
    nr = 0
    with open(path) as f:
        for line in f:
            o = json.loads(line)
            t = o.get("type")
            if t == "request":
                req_keys |= set(o)
                for k in META:
                    vals[k].add(json.dumps(o.get(k)))
                doms[o.get("domain")] = doms.get(o.get("domain"), 0) + 1
                for k in ("draft_p_min", "n_max", "n_min"):
                    if k in o: extra.setdefault("request." + k, set()).add(json.dumps(o[k]))
            elif t == "round" and nr < max_rounds:
                nr += 1
                rnd_keys |= set(o)
                for k in ("draft_p_min", "n_max", "n_min"):
                    if k in o: extra.setdefault("round." + k, set()).add(json.dumps(o[k]))
                for sub in ("draft", "dp", "params"):
                    if isinstance(o.get(sub), dict):
                        for k in ("draft_p_min", "n_max", "n_min", "p_min"):
                            if k in o[sub]: extra.setdefault("round.%s.%s" % (sub, k), set()).add(json.dumps(o[sub][k]))
                if isinstance(o.get("cand"), dict):
                    rnd_keys |= {"cand." + k for k in o["cand"]}
                    if isinstance(o["cand"].get("mtp"), dict):
                        rnd_keys |= {"cand.mtp." + k for k in o["cand"]["mtp"]}
    return dict(req_keys=sorted(req_keys), rnd_keys=sorted(rnd_keys), vals={k: sorted(v) for k, v in vals.items()},
                domains=doms, extra={k: sorted(v) for k, v in extra.items()})


if sha(FROZEN) != FROZEN_SHA:
    print("STOP: frozen script sha256 mismatch"); sys.exit(2)
ck, ref = schema(CK), schema(REF)
diff = dict(req_missing=sorted(set(ref["req_keys"]) - set(ck["req_keys"])),
            req_added=sorted(set(ck["req_keys"]) - set(ref["req_keys"])),
            rnd_missing=sorted(set(ref["rnd_keys"]) - set(ck["rnd_keys"])),
            rnd_added=sorted(set(ck["rnd_keys"]) - set(ref["rnd_keys"])))
ok = (not diff["req_missing"] and not diff["rnd_missing"] and ck["vals"]["schema"] == ['"strataplus.v1.1"']
      and ck["vals"]["data_kind"] == ['"teacher_forced"'] and ck["vals"]["dmax"] == ["7"]
      and set(ck["domains"]) == {"code", "chat", "edit"})
dp = [v for k, v in ck["extra"].items() if k.endswith("draft_p_min")]
has_nmax = any(k.endswith("n_max") for k in ck["extra"]); has_nmin = any(k.endswith("n_min") for k in ck["extra"])
meta_ok = bool(dp) and all(x in ('0.0', '0') for v in dp for x in v) and has_nmax and has_nmin
gate = dict(check_v12=ck, ref_v11=dict(req_keys=ref["req_keys"], rnd_keys=ref["rnd_keys"]), diff=diff,
            schema_ok=ok, draft_p_min_nmax_nmin_ok=meta_ok, check_v12_sha256=sha(CK))
json.dump(gate, open(os.path.join(OUTD, "schema_gate.json"), "w"), indent=1)
print(json.dumps(dict(diff=diff, vals=ck["vals"], domains=ck["domains"], extra=ck["extra"], schema_ok=ok, meta_ok=meta_ok), indent=1))
if not ok or not meta_ok:
    print("STOP: schema/metadata differ from v1.1 or draft_p_min/n_max/n_min missing; nothing adapted"); sys.exit(3)

import strata_sim.postprocess as pp
_orig, _cache = pp.load_tf, {}


def load_check(path, *a, **kw):
    d = os.path.basename(path).split("_")[1]          # holdout_{d}_tf_d7.jsonl -> d
    if "all" not in _cache:
        _cache["all"] = _orig(CK, *a, **kw)
    return [r for r in _cache["all"] if r["domain"] == d]


pp.load_tf = load_check
sys.argv = [FROZEN, OUTD]
runpy.run_path(FROZEN, run_name="__main__")
print("frozen script done on check_v12", flush=True)
