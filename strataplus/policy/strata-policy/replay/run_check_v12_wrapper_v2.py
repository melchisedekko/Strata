"""Wrapper v2 (Lead authorization 06:50 CET) — NEW file; v1 (run_check_v12_wrapper.py, sha256 c1d47afa…) untouched.
v1 stopped (rc=3, 06:44:31 CET) because it looked for draft_p_min / n_max / n_min only at the top level, while check_v12
carries them in request.spec_params.  v2 = v1 except the metadata gate, which now reads request.spec_params:
  draft_p_min -> draft_p_min (must be 0.0), draft_n_max_impl -> n_max (must be 7 = dmax), draft_n_min -> n_min (must be 0);
  accepted only if IDENTICAL in all 60 requests and coherent with the manifest: MANIFEST sha256 22073b2a…, marker
  80f25713… pointing at that manifest, check_v12_tf_d7.jsonl sha256 = its manifest entry, cmds.txt (manifest-verified)
  TF line with --dmax 7 --spec-draft-n-max 7 and no --spec-draft-p-min / --spec-draft-n-min.
The only accepted schema difference vs v1.1 is the added request key spec_params (anything else -> STOP exit 3).
Everything else (frozen script sha check, schema checks, load_tf replacement, runpy) identical to v1.
usage: nice -n 19 python3 run_check_v12_wrapper_v2.py OUTDIR"""
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
CKD = os.path.dirname(CK)
MAN, MARK, CMDS = os.path.join(CKD, "MANIFEST.sha256"), os.path.join(CKD, "CHECK_V12_READY"), os.path.join(CKD, "cmds.txt")
man = dict(reversed(l.split()) for l in open(MAN) if l.strip())
mk = json.load(open(MARK))
tfline = [l for l in open(CMDS) if "--mode tf" in l]
man_ok = (sha(MAN) == "22073b2a427c0c4207d1faa3a1125b431a6e949cef99d102d4408cd9034fbf09"
          and sha(MARK) == "80f257131555847dfc7cd65e17dceda6320ea1c1d2fcc77d8c8e23b7fcbec65a"
          and mk.get("manifest_sha256") == sha(MAN) and mk.get("files") == len(man) == 10
          and all(sha(os.path.join(CKD, f)) == h for f, h in man.items()))
sp = []
with open(CK) as f:
    for line in f:
        o = json.loads(line)
        if o.get("type") == "request":
            s = o.get("spec_params") or {}
            sp.append(json.dumps({"draft_p_min": s.get("draft_p_min"), "n_max": s.get("draft_n_max_impl"),
                                  "n_min": s.get("draft_n_min")}, sort_keys=True))
spv = sorted(set(sp)); m0 = json.loads(spv[0]) if len(spv) == 1 else {}
cmd_ok = (len(tfline) == 1 and "--dmax 7" in tfline[0] and "--spec-draft-n-max 7" in tfline[0]
          and "--spec-draft-p-min" not in tfline[0] and "--spec-draft-n-min" not in tfline[0])
meta_ok = (len(sp) == 60 and len(spv) == 1 and m0.get("draft_p_min") == 0.0 and m0.get("n_max") == 7
           and m0.get("n_min") == 0 and man_ok and cmd_ok)
ok = ok and diff["req_added"] == ["spec_params"] and not diff["rnd_added"]
ck["spec_params_mapped"] = dict(n_requests=len(sp), distinct=spv, manifest_ok=man_ok, cmds_tf_ok=cmd_ok)
gate = dict(check_v12=ck, ref_v11=dict(req_keys=ref["req_keys"], rnd_keys=ref["rnd_keys"]), diff=diff,
            schema_ok=ok, draft_p_min_nmax_nmin_ok=meta_ok, check_v12_sha256=sha(CK))
json.dump(gate, open(os.path.join(OUTD, "schema_gate.json"), "w"), indent=1)
print(json.dumps(dict(diff=diff, vals=ck["vals"], domains=ck["domains"], extra=ck["extra"], spec_params_mapped=ck["spec_params_mapped"], schema_ok=ok, meta_ok=meta_ok), indent=1))
if not ok or not meta_ok:
    print("STOP (v2): schema differs from v1.1 beyond spec_params, or spec_params/manifest check failed; nothing adapted"); sys.exit(3)

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
print("frozen script done on check_v12 (wrapper v2)", flush=True)
