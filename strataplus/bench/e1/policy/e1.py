#!/usr/bin/env python3
"""E1 (piano v2 §5/§8): model-free upper bound for H2 — per-request lookup vs cross-request pool, both with the
PRODUCTION SuffixDrafter (strata-src @ 7dd5cf18, via ctypes: /workspace/strata-policy/replay/native).

  y = REFERENCE text of public datasets / git history, tokenised with the Qwen3.5-2B tokenizer.
      It is NOT the greedy output of any model: acceptances are those a drafter would get if the model wrote y.
  lookup = SuffixDrafter reset per request, prompt appended, then y teacher-forced (as generate.cpp:14177-14178,
           15156): at position i it proposes from prompt + y[:i].
  pool   = one SuffixDrafter never reset inside a pool scope (a session or a whole domain): previous prompts and
           outputs + current prompt + y[:i].  Feed order: prompt, then committed tokens (log_format.md D10).
No MTP, no cost measurement: tok/s are computed with the symbolic profiles of piano §4 (P1/P2 = estimates
published in the code, not measurements; B-flat, B-lin bounds).
"""
from __future__ import annotations
import json, os, subprocess, sys, time, argparse
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/workspace/strata-policy/replay")
from strata_sim.native import NativeSuffixDrafter  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402

DATA = os.path.join(HERE, "data")


def _private(key):
    """Valore SOLO LOCALE (mai pubblicato) del dataset di edit con licenza non pubblicabile (etichetta pubblica: edit_np).
    Ordine: variabile d'ambiente `key`; altrimenti il file locale STRATAPLUS_PRIVATE_ENV
    (default /workspace/lic_rm/edit_dataset.env, righe KEY=VALORE). Se manca: errore esplicito."""
    v = os.environ.get(key, "").strip()
    path = os.environ.get("STRATAPLUS_PRIVATE_ENV", "/workspace/lic_rm/edit_dataset.env")
    if not v and os.path.isfile(path):
        for line in open(path):
            k, _, x = line.strip().partition("=")
            if k == key:
                v = x.strip()
    if not v:
        sys.exit(f"ERRORE: {key} non impostata (ne' in ambiente ne' in {path}). "
                 "Impostala o crea il file locale: vedi /workspace/lic_rm/README_edit_dataset.md")
    return v

SRC = "/workspace/strata-src"
DMAX = 7
KS = (5, 7)               # 5 = lookup k of the default --spec 6 (S-1); 7 = Dmax
MIN_MATCH, MAX_MATCH = 3, 64   # engine: --suffix-draft default 3, max_match 64
PROFILES = {               # s(T) T=1..8 (piano §4); rho_lu applied in e1_report.py
    "P1": ([1, 1.35, 1.7, 2.05, 2.45, 2.85, 3.25, 3.6], 0.0005),
    "P2": ([1, 1.30, 1.67, 1.99, 2.43, 2.83, 3.25, 3.67], 0.0005),
    "B-flat": ([1.0] * 8, 0.0005),
    "B-lin": ([float(t) for t in range(1, 9)], 0.0005),
}
TEMPLATE = "<|im_start|>user\n{u}<|im_end|>\n<|im_start|>assistant\n"


def git(*a):
    return subprocess.run(["git", "-C", SRC, *a], capture_output=True, text=True, errors="replace").stdout


def load_requests(n_chat=400, seed=0):
    R = []
    he = pd.read_parquet(f"{DATA}/ds_openai_humaneval/openai_humaneval/test-00000-of-00001.parquet")
    for r in he.itertuples():
        R.append(dict(domain="code", scope="code", src="humaneval", id=r.task_id,
                      prompt=TEMPLATE.format(u="Complete this Python function.\n" + r.prompt) + r.prompt,
                      y=r.canonical_solution))
    mb = pd.read_parquet(f"{DATA}/ds_mbpp/full/test-00000-of-00001.parquet")
    for r in mb.itertuples():
        R.append(dict(domain="code", scope="code", src="mbpp", id=f"mbpp/{r.task_id}",
                      prompt=TEMPLATE.format(u=r.text + "\nYour code should pass these tests:\n" + "\n".join(r.test_list)),
                      y=r.code))
    dl = pd.read_json(f"{DATA}/ds_databricks-dolly-15k/databricks-dolly-15k.jsonl", lines=True)
    dl = dl.sample(n=n_chat, random_state=seed)
    for i, r in enumerate(dl.itertuples()):
        u = r.instruction + (("\n\n" + r.context) if r.context else "")
        R.append(dict(domain="chat", scope="chat", src=f"dolly/{r.category}", id=f"dolly/{r.Index}",
                      prompt=TEMPLATE.format(u=u), y=r.response))
    ce = pd.read_parquet(f"{DATA}/ds_{_private('STRATAPLUS_EDIT_NAME')}/data/test-00000-of-00001.parquet")
    for r in ce.itertuples():
        R.append(dict(domain="edit", scope="edit", src=_private("STRATAPLUS_EDIT_TAG"), id=f"{_private('STRATAPLUS_EDIT_TAG')}/{r.id}",
                      prompt=TEMPLATE.format(u=getattr(r, _private("STRATAPLUS_EDIT_FIELD_INSTR")) + "\n\n```python\n" + r.before + "\n```"),
                      y="```python\n" + r.after + "\n```"))
    R += git_sessions()
    return R


def new_side_hunks(diff_text, ctx_lines=3):
    """Text the agent would emit for an edit: new side of each hunk (context + added lines), with the @@ header."""
    out, cur = [], []
    for ln in diff_text.splitlines():
        if ln.startswith("@@"):
            if cur: out.append("\n".join(cur))
            cur = [ln]
        elif cur and (ln.startswith(" ") or ln.startswith("+")) and not ln.startswith("+++"):
            cur.append(ln[1:])
    if cur: out.append("\n".join(cur))
    return "\n".join(out)


def old_excerpts(diff_text):
    """Short-context variant: only the old side of each hunk (what an agent sees if it sends file excerpts)."""
    out, cur = [], []
    for ln in diff_text.splitlines():
        if ln.startswith("@@"):
            if cur: out.append("\n".join(cur))
            cur = []
        elif ln.startswith(" ") or (ln.startswith("-") and not ln.startswith("---")):
            cur.append(ln[1:])
    if cur: out.append("\n".join(cur))
    return "\n...\n".join(out)


def git_sessions(min_commits=8, max_file_chars=200_000, max_per_session=30):
    files = {}
    for ln in git("log", "--name-only", "--format=").splitlines():
        if ln.strip(): files[ln] = files.get(ln, 0) + 1
    skip = lambda f: f.startswith("README.") and f != "README.md"   # translations duplicate README.md
    sess = [f for f, c in files.items() if c >= min_commits and not skip(f)]
    R = []
    for f in sorted(sess):
        commits = git("log", "--reverse", "--format=%H", "--", f).split()
        n = 0
        for c in commits:
            parent = git("rev-parse", "--verify", "-q", c + "^").strip()
            if not parent: continue
            before = git("show", f"{parent}:{f}")
            if not before or len(before) > max_file_chars: continue
            diff = git("diff", "-U3", parent, c, "--", f)
            y = new_side_hunks(diff)
            if len(y) < 20: continue
            msg = git("log", "-1", "--format=%s%n%b", c).strip()
            for variant, ctx in (("full", f"File {f}:\n```\n{before}\n```"), ("excerpt", f"File {f} (excerpts):\n```\n{old_excerpts(diff)}\n```")):
                R.append(dict(domain=f"session_{variant}", scope=f"{variant}:{f}", src="strata-git", id=f"{c[:10]}:{f}",
                              prompt=TEMPLATE.format(u=f"Apply this change: {msg}\n\n{ctx}\nReply with the edited hunks."), y=y))
            n += 1
            if n >= max_per_session: break
    return R


def walk(k, acc, K):
    """Lookup-only teacher-forced walk: draft min(k,K) tokens whenever the drafter proposes, else a plain step.
    Returns N tokens, rounds, rows histogram by T, wasted rows, P(a>=j | T>j) counts. Cost is applied afterwards
    (cost depends only on the T histogram): cost = sum_T cnt[T]*s(T) + rho_lu*(drafted rows + rounds without draft)."""
    n = len(k); i = 0; N = R = wasted = 0
    cntT = np.zeros(K + 2, np.int64); hist = np.zeros(K + 1, np.int64); reach = np.zeros(K + 1, np.int64)
    kk_all = np.minimum(k, K)
    while i < n:
        kk = int(kk_all[i]); a = min(int(acc[i]), kk, n - i - 1)
        cntT[kk + 1] += 1; N += a + 1; R += 1; wasted += kk - a
        if kk:
            reach[1:kk + 1] += 1; hist[1:a + 1] += 1
        i += a + 1
    return N, R, cntT, wasted, hist, reach


def boot_ci(groups, fn, B=2000, seed=0):
    """Cluster bootstrap: groups = list of per-cluster stat arrays; fn(sum over sampled clusters) -> scalar."""
    rng = np.random.default_rng(seed)
    G = np.stack(groups); m = len(G)
    vals = np.array([fn(G[rng.integers(0, m, m)].sum(0)) for _ in range(B)])
    return float(fn(G.sum(0))), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); args = ap.parse_args()
    t0 = time.time()
    tok = Tokenizer.from_file(f"{DATA}/tok_Qwen3.5-2B/tokenizer.json")
    reqs = load_requests(n_chat=100 if args.quick else 400)
    if args.quick: reqs = reqs[::5]
    for q in reqs:
        q["P"] = np.array(tok.encode(q["prompt"], add_special_tokens=False).ids, np.int32)
        q["Y"] = np.array(tok.encode(q["y"], add_special_tokens=False).ids, np.int32)
    reqs = [q for q in reqs if len(q["Y"]) >= 2]
    print(f"{len(reqs)} requests tokenised ({time.time()-t0:.1f}s)", flush=True)
    # pool scopes: "session" = one file history (session_* domains only), "domain" = all requests of the domain
    def scopes(q):
        out = [("domain", q["domain"])]
        if q["domain"].startswith("session_"): out.append(("session", q["scope"]))
        return out
    total, last = {}, {}
    for idx, q in enumerate(reqs):
        for sk in scopes(q):
            total[sk] = total.get(sk, 0) + len(q["P"]) + len(q["Y"]); last[sk] = idx
    lk_cap = max(len(q["P"]) + len(q["Y"]) for q in reqs) + 4096       # engine: max_context + 4096
    lk = NativeSuffixDrafter(MIN_MATCH, MAX_MATCH, lk_cap)
    pools = {}; pool_info = {}
    rows_out = []
    for idx, q in enumerate(reqs):
        P, Y = q["P"], q["Y"]
        lk.reset(); lk.append(P)
        kl, ml, al, _ = lk.scan(Y, DMAX, want_tokens=False)
        res = dict(domain=q["domain"], scope=q["scope"], src=q["src"], id=q["id"], n_prompt=len(P), n_y=len(Y))
        srcs = {"lookup": (kl, ml, al)}
        for sk in scopes(q):
            pscope = sk[0]
            if sk not in pools: pools[sk] = NativeSuffixDrafter(MIN_MATCH, MAX_MATCH, total[sk] + 4096)
            pd_ = pools[sk]; pd_.append(P)
            kp, mp, ap_, _ = pd_.scan(Y, DMAX, want_tokens=False)
            res[f"pool_{pscope}_hist"] = int(pd_.size())
            srcs[f"pool_{pscope}"] = (kp, mp, ap_)
            take = (ap_ > al) | ((ap_ == al) & (kp < kl))       # per-position oracle pick (upper bound of an arbiter)
            srcs[f"best_{pscope}"] = (np.where(take, kp, kl), np.where(take, mp, ml), np.maximum(ap_, al))
            fb = kl > 0                                          # deterministic: lookup if it proposes, else pool
            srcs[f"fallback_{pscope}"] = (np.where(fb, kl, kp), np.where(fb, ml, mp), np.where(fb, al, ap_))
            if last[sk] == idx:
                pool_info[f"{pscope}:{sk[1]}"] = dict(hist_tokens=int(pd_.size()), capacity=total[sk] + 4096)
                del pools[sk]
        for sname, (k, m, a) in srcs.items():
            cov = k > 0
            res[f"{sname}.cov"] = int(cov.sum()); res[f"{sname}.acc_sum"] = int(a[cov].sum())
            res[f"{sname}.hit1"] = int((a[cov] >= 1).sum())
            for lo, hi in ((3, 4), (4, 8), (8, 16), (16, 65)):
                sel = cov & (m >= lo) & (m < hi)
                res[f"{sname}.m{lo}.n"] = int(sel.sum()); res[f"{sname}.m{lo}.hit1"] = int((a[sel] >= 1).sum())
                res[f"{sname}.m{lo}.acc"] = int(a[sel].sum())
            for K in KS + ("G7", "G12"):
                if K == "G7":   # gated: draft only when match >= 6 (first DraftPolicy bucket edge, draft_policy.cpp:32-34)
                    N, Rr, cntT, wasted, hist, reach = walk(np.where(m >= 6, k, 0), a, 7); K = 7; tag = "G7"
                elif K == "G12":
                    N, Rr, cntT, wasted, hist, reach = walk(np.where(m >= 12, k, 0), a, 7); K = 7; tag = "G12"
                else:
                    N, Rr, cntT, wasted, hist, reach = walk(k, a, K); tag = f"K{K}"
                res[f"{sname}.{tag}.N"] = N; res[f"{sname}.{tag}.R"] = Rr; res[f"{sname}.{tag}.wasted"] = int(wasted)
                for T in range(1, K + 2): res[f"{sname}.{tag}.T{T}"] = int(cntT[T])
                for j in range(1, K + 1):
                    res[f"{sname}.{tag}.reach{j}"] = int(reach[j]); res[f"{sname}.{tag}.hit{j}"] = int(hist[j])
        rows_out.append(res)
        if idx % 200 == 0: print(f"  {idx}/{len(reqs)} {time.time()-t0:.0f}s", flush=True)
    df = pd.DataFrame(rows_out)
    out = os.path.join(HERE, "results"); os.makedirs(out, exist_ok=True)
    df.to_csv(os.path.join(out, "e1_per_request.csv"), index=False)
    json.dump(dict(pools=pool_info, slot_bytes=32, note="SuffixDrafter table = next_pow2(2*capacity) slots x 32 B + 4 B/token history"),
              open(os.path.join(out, "pool_sizes.json"), "w"), indent=1)
    print(f"done {len(df)} requests in {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
