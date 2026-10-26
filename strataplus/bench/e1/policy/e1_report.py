#!/usr/bin/env python3
"""Aggregates results/e1_per_request.csv -> results/E1_results.md (+ e1_summary.json). Cluster bootstrap IC95."""
import json, os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "results")
df = pd.read_csv(os.path.join(OUT, "e1_per_request.csv"))
RHO_LU = 0.001       # ~20 us/token (SuffixDecoding, via Scout) / ~20.5 ms step (P2 step_ms): hypothesis
PROF = {"P1": [1, 1.35, 1.7, 2.05, 2.45, 2.85, 3.25, 3.6], "P2": [1, 1.30, 1.67, 1.99, 2.43, 2.83, 3.25, 3.67],
        "B-flat": [1.0] * 8, "B-lin": [float(t) for t in range(1, 9)]}
B = 2000
rng = np.random.default_rng(0)


def stats(d, s, K, tag=None):
    """per-request vector: N, R, cost per profile, wasted, rows"""
    tag = tag or f"K{K}"
    T = np.stack([d[f"{s}.{tag}.T{t}"].values for t in range(1, K + 2)], 1)
    rows = (T * np.arange(K + 1)).sum(1)
    cols = [d[f"{s}.{tag}.N"].values, d[f"{s}.{tag}.R"].values, d[f"{s}.{tag}.wasted"].values, rows]
    for p, sv in PROF.items():
        cols.append((T * np.array(sv[:K + 1])).sum(1) + RHO_LU * (rows + T[:, 0]))
    return np.stack(cols, 1).astype(float)


def boot(groups_a, groups_b, f):
    m = len(groups_a); A = groups_a; Bm = groups_b
    v = f(A.sum(0), Bm.sum(0))
    vals = []
    for _ in range(B):
        idx = rng.integers(0, m, m)
        vals.append(f(A[idx].sum(0), Bm[idx].sum(0)))
    return v, np.percentile(vals, 2.5), np.percentile(vals, 97.5)


def cluster(d, arr):
    key = d["scope"].values if d["domain"].iloc[0].startswith("session_") else d["id"].values
    g = pd.Series(range(len(d))).groupby(key).apply(list)
    return np.stack([arr[ix].sum(0) for ix in g])


lines = ["# E1 — limite superiore model-free per H2 (pool persistente vs lookup per richiesta)", "",
         "**Natura dei dati:** testi REALI di riferimento (non output greedy di un modello), tokenizzati con il tokenizer Qwen3.5-2B; "
         "accettazione = LCP(proposta, y[pos:]) con `SuffixDrafter` di PRODUZIONE (strata-src @ 7dd5cf18, via ctypes). "
         "Nessun MTP. tok/s **stimati** con i profili simbolici del piano §4 (P1/P2 = stime pubblicate nel codice, non misure; "
         f"B-flat/B-lin = limiti), ρ_lu = {RHO_LU} per token proposto o sondato (ipotesi ≈20 µs/token su ~20,5 ms di step). "
         "Walk teacher-forced *lookup-only*: si drafta min(k,K) ogni volta che il drafter propone, altrimenti step normale. "
         "IC95 = bootstrap a cluster (sessione = storia di un file per i domini session_*, richiesta altrimenti), 2000 campioni, appaiato.", ""]
summary = {}
for dom, d in df.groupby("domain", sort=False):
    d = d.reset_index(drop=True)
    pools = ["pool_domain", "fallback_domain", "best_domain"] + (["pool_session", "fallback_session", "best_session"] if dom.startswith("session_") else [])
    nclus = len(set(d["scope"])) if dom.startswith("session_") else len(d)
    lines += [f"## Dominio `{dom}` — {len(d)} richieste, {nclus} cluster, {int(d.n_y.sum())} token di y, sorgenti: {', '.join(sorted(set(s.split('/')[0] for s in d.src)))}", ""]
    lines += ["| sorgente | copertura (pos. con proposta) | P(a≥1 \\| proposta) | acc. media \\| proposta | AL K=5 | AL K=7 | righe sprecate M4 (K=7) |", "|---|---|---|---|---|---|---|"]
    for s in ["lookup"] + pools:
        n = d.n_y.sum(); cov = d[f"{s}.cov"].sum()
        al5 = d[f"{s}.K5.N"].sum() / d[f"{s}.K5.R"].sum(); al7 = d[f"{s}.K7.N"].sum() / d[f"{s}.K7.R"].sum()
        st = stats(d, s, 7); w = st[:, 2].sum() / max(st[:, 3].sum(), 1)
        lines.append(f"| {s} | {cov/n:.1%} | {d[f'{s}.hit1'].sum()/max(cov,1):.1%} | {d[f'{s}.acc_sum'].sum()/max(cov,1):.2f} | {al5:.3f} | {al7:.3f} | {w:.1%} |")
    lines += ["", "Guadagno relativo vs lookup per richiesta (IC95), K=7: AL e speedup stimato = N·s(1)/ΣT_round", "",
              "| sorgente | ΔAL | Δspeedup P1 | Δspeedup P2 | Δspeedup B-flat | Δspeedup B-lin |", "|---|---|---|---|---|---|"]
    base = cluster(d, stats(d, "lookup", 7))
    for s in pools:
        alt = cluster(d, stats(d, s, 7))
        cells = []
        r = boot(alt, base, lambda a, b: (a[0] / a[1]) / (b[0] / b[1]) - 1); cells.append(r)
        for j, p in enumerate(PROF):
            cells.append(boot(alt, base, lambda a, b, j=j: (b[4 + j]) / (a[4 + j]) - 1))   # same N: speedup ratio = cost ratio
        summary[f"{dom}/{s}"] = [list(map(float, c)) for c in cells]
        lines.append(f"| {s} | " + " | ".join(f"{v:+.1%} [{lo:+.1%}, {hi:+.1%}]" for v, lo, hi in cells) + " |")
    for tag in ("G7", "G12"):
        lines += ["", f"Walk con gate sul match ({'match≥6' if tag=='G7' else 'match≥12'}, K=7): speedup stimato assoluto e Δ vs lookup con lo stesso gate (IC95)", "",
                  "| sorgente | AL | speedup P1 | speedup P2 | Δspeedup P1 | Δspeedup P2 | Δspeedup B-lin |", "|---|---|---|---|---|---|---|"]
        bg = stats(d, "lookup", 7, tag); bgc = cluster(d, bg)
        for s in ["lookup"] + pools:
            st = stats(d, s, 7, tag); c = cluster(d, st)
            row = f"| {s} | {st[:,0].sum()/st[:,1].sum():.3f} | {st[:,0].sum()/st[:,4].sum():.3f} | {st[:,0].sum()/st[:,5].sum():.3f} | "
            if s == "lookup":
                row += "— | — | — |"
            else:
                cells = [boot(c, bgc, lambda a, b, j=j: b[4 + j] / a[4 + j] - 1) for j in (0, 1, 3)]
                summary[f"{dom}/{s}/{tag}"] = [list(map(float, x)) for x in cells]
                row += " | ".join(f"{v:+.1%} [{lo:+.1%}, {hi:+.1%}]" for v, lo, hi in cells) + " |"
            lines.append(row)
    # absolute speedups
    lines += ["", "Speedup stimato assoluto (K=7) N·s(1)/ΣT_round: " + "; ".join(
        f"{s}: " + ", ".join(f"{p} {stats(d, s, 7)[:, 0].sum() / stats(d, s, 7)[:, 4 + j].sum():.3f}" for j, p in enumerate(PROF))
        for s in ["lookup", pools[0]]), ""]
    # per position P(a>=j | T>j)
    for s in ["lookup", pools[0]]:
        pj = [d[f"{s}.K7.hit{j}"].sum() / max(d[f"{s}.K7.reach{j}"].sum(), 1) for j in range(1, 8)]
        lines.append(f"P(a≥j | T>j), {s}, j=1..7: " + " ".join(f"{x:.2f}" for x in pj))
    # match buckets
    lines += ["", "P(a≥1 | match bucket) [n]: " + "; ".join(
        f"{s}: " + ", ".join(f"m{lo}: {d[f'{s}.m{lo}.hit1'].sum()/max(d[f'{s}.m{lo}.n'].sum(),1):.2f} [{d[f'{s}.m{lo}.n'].sum()}]" for lo in (3, 4, 8, 16))
        for s in ["lookup", pools[0]]), ""]
ps = json.load(open(os.path.join(OUT, "pool_sizes.json")))
big = sorted(ps["pools"].items(), key=lambda x: -x[1]["hist_tokens"])
def mem(cap, h):
    c = 1
    while c < 2 * cap: c <<= 1
    return (c * 32 + 4 * h) / 2**20
lines += ["## Memoria del pool", "",
          "SuffixDrafter: tabella = next_pow2(2·capacità) slot × 32 B (+4 B/token di storia). Per avere la stessa qualità serve "
          "capacità ≥ storia; a tabella piena i nuovi trigrammi non vengono più indicizzati (find_slot → nullptr, suffix_drafter.cpp:48) "
          "→ un pool reale ha bisogno di eviction (finestra o LRU per richiesta, come `max_cached_requests` di SuffixDecoding).", "",
          "| pool | token di storia | MiB con capacità = storia |", "|---|---|---|"]
for k, v in big[:6]:
    lines.append(f"| {k} | {v['hist_tokens']} | {mem(v['hist_tokens'], v['hist_tokens']):.1f} |")
lines.append(f"\nRiferimento: llama.cpp ngram-mod ≈16 MB (piano v2). Con la struttura attuale 16 MiB corrispondono a ~{(16*2**20)//(64+4)//1000}k token di storia (≈64 B/slot effettivi a carico 0,5).")
open(os.path.join(OUT, "E1_results.md"), "w").write("\n".join(lines) + "\n")
json.dump(summary, open(os.path.join(OUT, "e1_summary.json"), "w"), indent=1)
print("\n".join(lines))
