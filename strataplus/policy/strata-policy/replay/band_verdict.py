"""Verdetto a due fasce (Strata Lead): 'Strata-plausibile' rho_mtp in [0.06,0.15] = fascia plausibile, stima di Scout,
da misurare su Strata (decide la patch); 'proxy' rho_mtp = 0.26 (P4 grezzo, provvisorio) = solo controllo di robustezza.
Legge <run>/p4.json, scrive <run>/band_verdict.md. Criterio piano §8: IC95>0 in >=2/3 domini, nessun dominio IC95<0."""
import json, sys
run = sys.argv[1]; J = json.load(open(run + "/p4.json")); G = J["grid"]; doms = ["code", "chat", "edit"]
shapes = ["P1", "P2", "P4"]; rhos = J["rhos"]
band = [r for r in rhos if r <= 0.15]; proxy = [r for r in rhos if r >= 0.255]
f = lambda b: "%+.1f%% [%+.1f, %+.1f]" % (100 * b[0], 100 * b[1], 100 * b[2])
CMP = [("gate_v2", "vs_current", "H1: gate_v2 vs DraftPolicy default"), ("gate_v2", "vs_cost", "H4(a): gate_v2 vs STRATA_SPEC_COST=1"),
       ("gate_v2", "vs_k3", "H4(b): gate_v2 vs k=3"), ("gate_v2", "vs_specu", "Lead: gate_v2 vs euristica Specu"),
       ("gate_v2", "vs_specu_costdepth", "(info) gate_v2 vs Specu+profondità SPEC_COST"),
       ("specu", "vs_current", "Specu vs default"), ("specu", "vs_cost", "Specu vs STRATA_SPEC_COST=1"), ("specu", "vs_k3", "Specu vs k=3"),
       ("specu_costdepth", "vs_cost", "(info) Specu+prof. SPEC_COST vs STRATA_SPEC_COST=1")]
L = ["# Verdetto a due fasce — " + J["label"], "",
     "Fascia **Strata-plausibile** rho_mtp ∈ {%s}: *fascia plausibile, stima di Scout, da misurare su Strata* (non è una misura); decide la patch. "
     "Fascia **proxy** rho_mtp = %s (P4 grezzo, provvisorio): solo robustezza. Forme s(T): P1, P2 (stime da codice), P4 (misurata su CPU, "
     "denso, non AMD, provvisoria). Costo additivo s(T)+d·rho_mtp. Ogni cella: Δ tok/s stimato [IC95 bootstrap a cluster]." % (
         ", ".join("%.3f" % r for r in band), ", ".join("%.3f" % r for r in proxy)), ""]
for fascia, rr in (("Strata-plausibile [0.06, 0.15]", band), ("proxy 0.26 (robustezza)", proxy)):
    L += ["## Fascia " + fascia, "", "| confronto | esito (profili OK / tot) | profili con un dominio IC95<0 | " +
          " | ".join("%s: min…max Δ (IC95 della cella peggiore)" % d for d in doms) + " |", "|---|---|---|---|---|---|"]
    for cand, key, title in CMP:
        cells = [(s, r) for s in shapes for r in rr]
        ok = neg = 0; per = {d: [] for d in doms}
        for s, r in cells:
            bs = [G["%s|%s|rho%.4f" % (d, s, r)]["pol"][cand][key] for d in doms]
            ok += sum(b[1] > 0 for b in bs) >= 2 and not any(b[2] < 0 for b in bs); neg += any(b[2] < 0 for b in bs)
            for d, b in zip(doms, bs):
                per[d].append(b)
        cols = []
        for d in doms:
            lo = min(per[d], key=lambda b: b[0]); hi = max(per[d], key=lambda b: b[0])
            cols.append("%+.1f…%+.1f%% (peggiore %s)" % (100 * lo[0], 100 * hi[0], f(lo)))
        L.append("| %s | %s (%d/%d) | %d | %s |" % (title, "GO" if ok == len(cells) else "NO-GO", ok, len(cells), neg, " | ".join(cols)))
    L.append("")
L += ["## Dettaglio a rho_mtp = 0.099 (centro della fascia plausibile) e 0.26", "",
      "| forma | rho | dominio | gate_v2 vs default | vs SPEC_COST=1 | vs k3 | vs Specu | Specu vs SPEC_COST=1 | k fisso migliore |", "|---|---|---|---|---|---|---|---|---|"]
for s in shapes:
    for r in [x for x in rhos if abs(x - 0.0992) < 1e-3] + proxy:
        for d in doms:
            c = G["%s|%s|rho%.4f" % (d, s, r)]; p = c["pol"]
            L.append("| %s | %.3f | %s | %s | %s | %s | %s | %s | %d |" % (s, r, d, f(p["gate_v2"]["vs_current"]), f(p["gate_v2"]["vs_cost"]),
                     f(p["gate_v2"]["vs_k3"]), f(p["gate_v2"]["vs_specu"]), f(p["specu"]["vs_cost"]), c["best_fixed_k"]))
open(run + "/band_verdict.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))
