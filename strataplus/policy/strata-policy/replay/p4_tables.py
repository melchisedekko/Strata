import json,sys
def f(t,pct=True):
    p,lo,hi=t; s=100 if pct else 1
    return f"{p*s:+.1f}% [{lo*s:+.1f}, {hi*s:+.1f}]" if pct else f"{p:.2f} [{lo:.2f}, {hi:.2f}]"
def g(t): p,lo,hi=t; return f"{p*100:.1f}% [{lo*100:.1f}, {hi*100:.1f}]"
run,title=sys.argv[1],sys.argv[2]
d=json.load(open(run+'/p4.json'))['main']
print(f"**{title}** — Δ tok/s stimato [IC95]; profili P1/P2 (ρ_mtp 0.059, stime da codice), P4 (ρ_mtp 0.258, misurato su CPU, modello denso, non AMD, provvisorio)\n")
print("| dominio | profilo | speedup gate_v2 vs no-spec | gate_v2 vs default | vs STRATA_SPEC_COST=1 | vs k=3 | vs Specu | gap residuo gate_v2 → O_round | G(O_round) default | G(O_depth) SPEC_COST (solo MTP) | k fisso migliore |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for dom in ['code','chat','edit']:
  for pr in ['P1','P2','P4']:
    c=d[f'{dom}|{pr}'];P=c['pol'];gv=P['gate_v2']
    print(f"| {dom} | {pr} | {f(gv['speedup_ci'],False)}× | {f(gv['vs_current'])} | {f(gv['vs_cost'])} | {f(gv['vs_k3'])} | {f(gv['vs_specu'])} | {g(gv['G_O_round'])} | {g(P['strata_current']['G_O_round'])} | {g(P['strata_cost_mtponly']['G_O_depth'])} | {c['best_fixed_k']} |")
