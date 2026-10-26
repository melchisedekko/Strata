"""results/v2/<run>/{summary,grid}.json -> report.md (M1-M5, oracle gaps, go/no-go per piano v2 §8, win map).
The label of the data (SYNTHETIC / teacher-forced proxy) is repeated in every section: nothing here is a live measurement."""
import json, os, sys

CAND = "gate_v2"          # main candidate (H1+H4 merged: one gate, source + MTP depth)
VARIANTS = ["gate_v2_conf", "gate_v2_pool", "gate_v2_native", "strata_cost_cf"]
SHOW = ["nospec", "mtp_fixed_k3", "strata_current", "strata_cost", "strata_cost_mtponly", "strata_current_pool",
        "strata_cost_cf", "gate_v2", "gate_v2_native", "gate_v2_conf", "gate_v2_noskip", "gate_v2_nolookup", "mtp_adaedl",
        "gate_v2_pool", "gate_v2_poolonly"]
MAIN_DOMS = ["code", "chat", "edit"]


def ci(v):
    return "%+.1f%% [%+.1f, %+.1f]" % (100 * v[0], 100 * v[1], 100 * v[2])


def sign(v):
    return "+" if v[1] > 0 else ("−" if v[2] < 0 else "=")


def main(run):
    S = json.load(open(os.path.join(run, "summary.json")))
    gp = os.path.join(run, "grid.json")
    G = json.load(open(gp))["grid"] if os.path.exists(gp) else None
    cells = S["cells"]
    doms = list(S["n_requests"])
    profs = list(S["profiles"])
    L = []
    w = L.append
    w("# Replay v2 — %s\n" % os.path.basename(run.rstrip("/")))
    w("**Dati:** %s\n" % S["label"])
    w("**Costi:** profili simbolici (%s). P1/P2 = stime da codice, B-flat/B-lin = limiti; P4 (misura CPU) %s.\n" % (
        "; ".join("%s = %s" % (k, v["label"]) for k, v in S["profiles"].items()),
        "presente" if "P4" in profs else "NON disponibile in questo run"))
    w("Richieste per dominio: %s; token: %s. IC95 = bootstrap per richiesta (cluster = sessione).\n" % (
        S["n_requests"], S["n_tokens"]))

    w("\n## M1 — AL e accettazione per posizione (profilo P1)\n")
    w("| dominio | policy | AL | P(a≥1) | P(a≥2) | P(a≥3) | P(a≥4) | quota none/mtp/lk/pl |")
    w("|---|---|---|---|---|---|---|---|")
    for d in doms:
        c = cells.get("%s|P1" % d)
        if not c:
            continue
        for n in ["mtp_fixed_k3", "strata_current", "strata_cost", CAND, "gate_v2_pool"]:
            p = c["policies"].get(n)
            if not p:
                continue
            pp = (p["p_pos"] + [float("nan")] * 4)[:4]
            sh = p["src_share"]
            w("| %s | %s | %.2f | %s | %s |" % (d, n, p["AL"], " | ".join("—" if x is None or x != x else "%.2f" % x for x in pp),
                                               "/".join("%.2f" % sh.get(k, 0) for k in ("none", "mtp", "lk", "pl"))))

    w("\n## M2–M4 — tok/s stimato, gap dagli oracoli, righe sprecate\n")
    w("G = 1 − tps/tps_oracolo. O_depth = fonte MTP fissata, T libero (gap di profondità H4).\n")
    for d in doms:
        w("\n### %s\n" % d)
        w("| profilo | policy | speedup | AL | sprecate | G O_round | G O_DP | G O_depth | Δ vs strata_current | Δ vs strata_cost |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        for pn in profs:
            c = cells.get("%s|%s" % (d, pn))
            if not c:
                continue
            for n in SHOW:
                p = c["policies"].get(n)
                if not p:
                    continue
                w("| %s | %s | %.3f | %.2f | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %s | %s |" % (
                    pn, n, p["speedup"], p["AL"], 100 * p["wasted"], 100 * p["G_vs_O_round"], 100 * p["G_vs_O_DP"],
                    100 * p["G_vs_O_depth"], ci(p["vs_strata_current"]), ci(p["vs_strata_cost"])))
            o = c["oracles"]
            w("| %s | *oracoli* | O_round %.3f, O_DP %.3f, O_DP senza pool %.3f, O_depth %.3f | | | | | | | |" % (
                pn, o["O_round"]["speedup"], o["O_DP"]["speedup"], o["O_DP_nopool"]["speedup"], o["O_depth"]["speedup"]))

    w("\n## M5 — identità greedy\n")
    w("Nel replay vale per costruzione (l'output è y, la policy sceglie solo cosa verificare). Il criterio reale è V1 "
      "(concordanza simulatore/live) e lo sha256 live con/senza spec: richiede run di Strata Bench.\n")

    # go/no-go
    w("\n## Go/no-go (piano v2 §8) — sui dati di questo run, NON su misure live\n")
    md = [d for d in MAIN_DOMS if d in doms]
    pr12 = [p for p in ("P1", "P2", "P4") if p in profs]

    def cellv(d, p, n, key):
        return cells["%s|%s" % (d, p)]["policies"][n][key]

    # H1 no-go
    small = all(cellv(d, p, "strata_current", "G_vs_O_round") < 0.03 for d in md for p in ("P1", "P2") if p in profs)
    w("**H1 no-go** (G(O_round) di DraftPolicy attuale < 3%% ovunque in P1,P2): %s. Valori: %s.\n" % (
        "SÌ → no-go" if small else "no (c'è margine)",
        ", ".join("%s/%s %.0f%%" % (d, p, 100 * cellv(d, p, "strata_current", "G_vs_O_round")) for d in md for p in ("P1", "P2") if p in profs)))

    def go(base_key, n=CAND):
        res = {}
        for p in pr12:
            v = [cellv(d, p, n, base_key) for d in md]
            pos = sum(1 for x in v if x[1] > 0)
            neg = sum(1 for x in v if x[2] < 0)
            res[p] = (pos >= 2 and neg == 0, v)
        same = len({r[0] for r in res.values()}) == 1
        return all(r[0] for r in res.values()) and same, res

    for title, key in (("H1 go: candidato vs DraftPolicy attuale (default)", "vs_strata_current"),
                       ("H4 go (a): candidato vs STRATA_SPEC_COST=1", "vs_strata_cost"),
                       ("H4 go (b): candidato vs MTP fisso k=3 (--spec 4)", "vs_mtp_fixed_k3")):
        for n in [CAND] + [x for x in VARIANTS if x.startswith("gate_v2") and x in cells["%s|P1" % md[0]]["policies"]]:
            ok, res = go(key, n)
            w("- **%s** [%s]: %s — %s" % (title, n, "GO" if ok else "no-go", "; ".join(
                "%s: %s" % (p, ", ".join("%s %s" % (d, ci(x)) for d, x in zip(md, r[1]))) for p, r in res.items())))
    if "P4" not in profs:
        w("\n*P4 assente: il criterio \"stesso segno sotto P1, P2 e P4\" è valutato solo su P1, P2 (provvisorio).*\n")
    h4 = all(cellv(d, p, "strata_cost", "G_vs_O_depth") < 0.03 for d in md for p in pr12)
    w("\n**H4 no-go** (gap di STRATA_SPEC_COST=1 da O_depth < 3%% ovunque): %s. Valori: %s.\n" % (
        "SÌ → no-go" if h4 else "no (c'è margine)",
        ", ".join("%s/%s %.0f%%" % (d, p, 100 * cellv(d, p, "strata_cost", "G_vs_O_depth")) for d in md for p in pr12)))

    # H2
    if "session" in doms:
        w("\n**H2 (pool persistente)** — gate_v2_pool vs gate_v2 (lookup per richiesta); AL = stima puntuale:\n")
        for d in doms:
            for p in pr12:
                a, b = cells["%s|%s" % (d, p)]["policies"]["gate_v2_pool"], cells["%s|%s" % (d, p)]["policies"][CAND]
                w("- %s/%s: AL %.2f→%.2f, tok/s %s" % (d, p, b["AL"], a["AL"], ci(a["vs_gate_v2"])))
    # robustness
    w("\n**Robustezza** (candidato ≥ baseline in tutte le celle, > in P1 e P2):\n")
    for base in ("vs_strata_current", "vs_strata_cost", "vs_mtp_fixed_k3"):
        for n in [CAND, "gate_v2_conf", "gate_v2_pool"]:
            if n not in cells["%s|P1" % md[0]]["policies"]:
                continue
            bad = [c for c in cells if c.split("|")[0] in md and cells[c]["policies"][n][base][2] < 0]
            strict = all(cellv(d, p, n, base)[1] > 0 for d in md for p in ("P1", "P2") if p in profs)
            w("- %s %s: %s; celle con IC95 interamente < 0: %s" % (n, base, "OK" if not bad and strict else "NON soddisfatta",
                                                              ", ".join(bad) or "nessuna"))

    if G:
        w("\n## M3 — mappa di sensibilità (α × ρ_mtp, ρ_lu ∈ {0, 0.001, 0.01})\n")
        w("Simbolo per cella: + = IC95 > 0, − = IC95 < 0, = = IC95 contiene 0. Riga = α (0 = verifica piatta/memory-bound, "
          "1 = lineare/compute-bound); colonne = ρ_mtp; tre simboli = ρ_lu 0 / 0.001 / 0.01.\n")
        alphas = sorted({k.split("|")[1].split("_")[1][1:] for k in G}, key=float)
        rms = sorted({k.split("|")[1].split("_")[2][1:] for k in G}, key=float)
        rls = sorted({k.split("|")[1].split("_")[3][1:] for k in G}, key=float)
        for comp, lab in (("gate_v2", "gate_v2 vs strata_current"), ("cost:gate_v2", "gate_v2 vs STRATA_SPEC_COST=1"),
                          ("k3:gate_v2", "gate_v2 vs k=3"), ("cost:gate_v2_conf", "gate_v2_conf vs STRATA_SPEC_COST=1"),
                          ("cost:gate_v2_pool", "gate_v2_pool vs STRATA_SPEC_COST=1")):
            for d in doms:
                w("\n**%s — %s**\n" % (lab, d))
                w("| α \\ ρ_mtp | " + " | ".join(rms) + " |")
                w("|---" * (len(rms) + 1) + "|")
                wins = tot = 0
                for a in alphas:
                    row = []
                    for rm in rms:
                        s = ""
                        for rl in rls:
                            v = G.get("%s|g_a%s_m%s_l%s" % (d, a, rm, rl), {}).get(comp)
                            s += sign(v) if v else "?"
                            if v:
                                tot += 1
                                wins += v[1] > 0
                        row.append(s)
                    w("| %s | %s |" % (a, " | ".join(row)))
                w("\nVince (IC95 > 0) in %d/%d celle della griglia." % (wins, tot))
    open(os.path.join(run, "report.md"), "w").write("\n".join(L) + "\n")
    print(os.path.join(run, "report.md"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/v2/synthetic")
