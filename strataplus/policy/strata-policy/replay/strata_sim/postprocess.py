"""strataplus.v1 (log_format.md) -> per-request arrays used by sim2.

Reads teacher-forced traces (data_kind teacher_forced, one round per output position with cand.mtp at Dmax) such as
Strata Bench's raw/tf_d7.jsonl or the annotated traces/<run_id>.jsonl. MTP candidates come from the trace (REAL model
output on the labelled hardware/engine); lookup and pool candidates are RECOMPUTED here with the production
SuffixDrafter (ctypes) on prompt_ids + y, because the trace's cand.lookup uses the Bench's own settings (G3) and the
pool (cand.pool) is not produced (G4). Label every result with the trace's `label` (e.g. "proxy CPU").
"""
from __future__ import annotations
import json
from collections import defaultdict
import numpy as np
from .native import NativeSuffixDrafter
from .synth2 import DMAX, lcp_rows, lcp_pair


def load_tf(path, min_match=3, max_match=64, rep=0, pool_scope="domain"):
    reqs, rounds, ends = [], defaultdict(dict), {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:          # run still writing: last line may be partial
                continue
            if o.get("rep", 0) != rep:
                continue
            if o.get("type") == "request":
                reqs.append(o)
            elif o.get("type") == "request_end":      # D13: live engine traces (patch P1) carry y here
                ends[o["req_id"]] = o.get("output_ids")
            elif o.get("type") == "round":
                rounds[o["req_id"]][o.get("gen_index", o.get("pos"))] = o
    out = []
    pools = {}
    for q in reqs:
        y = np.array(q.get("output_ids") or q.get("ref_tokens") or ends.get(q["req_id"]) or [], np.int32)
        P = np.array(q["prompt_ids"], np.int32)
        R = rounds.get(q["req_id"], {})
        n = len(y)
        if n < 2 or len(R) < n:
            continue
        tok = np.full((n, DMAX), -1, np.int32); p = np.zeros((n, DMAX), np.float32); ent = np.full((n, DMAX), np.nan, np.float32)
        bad = 0
        for i in range(n):
            r = R[i]
            tt = r.get("target_tokens")
            if tt and tt[0] != y[i]:
                bad += 1
            m = r["cand"]["mtp"]
            k = min(DMAX, len(m["tokens"]))
            tok[i, :k] = m["tokens"][:k]; p[i, :k] = m["probs"][:k]
            if "ent" in m:
                ent[i, :k] = m["ent"][:k]
        dom = q.get("domain", "?")
        lk = NativeSuffixDrafter(min_match, max_match, 1 << 15)
        lk.append(P)
        lk_k, lk_m, lk_acc, lk_tok = lk.scan(y, DMAX)
        key = dom if pool_scope == "domain" else q.get("session_id") or q["req_id"]
        if key not in pools:
            pools[key] = NativeSuffixDrafter(min_match, max_match, 1 << 18)
        pool = pools[key]
        pool.append(P)
        pl_k, pl_m, pl_acc, pl_tok = pool.scan(y, DMAX)
        out.append(dict(domain=dom, req=q["req_id"], session=q.get("session_id") or q["req_id"],
                        data_kind=q.get("data_kind", "teacher_forced"), label=q.get("label", ""), n=n, n_prompt=len(P),
                        y=y, kind=None, mtp_tok=tok, mtp_p=p, mtp_ent=ent, mtp_acc=lcp_rows(tok, y), target_mismatch=bad,
                        lk_k=lk_k, lk_m=lk_m, lk_acc=lk_acc, lk_tok=lk_tok, agree=lcp_pair(tok, lk_tok),
                        pl_k=pl_k, pl_m=pl_m, pl_acc=pl_acc, pl_tok=pl_tok, agree_pl=lcp_pair(tok, pl_tok)))
    return out
