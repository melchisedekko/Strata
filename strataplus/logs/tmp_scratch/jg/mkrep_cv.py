import json,statistics as st,sys
n=json.load(open('holdout_v11_costvariants.json')); c=n["additive"]["V1"]["cells"]; g=n["grid"]
ARMS=["A_ORIG","A_Mfull","A_Mreal","A_Mcap"]; REFS=["default_old","default_corr","spec_cost","k3"]
L=[]
def tab(kind):
  L.append("| dominio | variante | "+" | ".join(REFS)+" |"); L.append("|"+"---|"*(2+len(REFS)))
  for d in ("code","chat","edit"):
    ks=[k for k in c if k.startswith(d+"|") and (("rho0.2600" in k)==(kind=="ctrl"))]
    for a in ARMS:
      row=[]
      for r in REFS:
        cs=[c[k][a+"_vs_"+r] for k in ks]; pts=[x["ci"][0]*100 for x in cs]
        w=sum(x["cls"]=="worse" for x in cs); b=sum(x["cls"]=="better" for x in cs)
        row.append("%+.1f%% [%+.1f;%+.1f] W%d/B%d/%d"%(st.median(pts),min(pts),max(pts),w,b,len(cs)))
      L.append("| %s | %s | %s |"%(d,a,(" | ".join(row))))
L.append("### Banda ρ 0,06–0,15 (P1/P2/P4 × 5 ρ = 15 celle/dominio), V1 (V2 identico)\nmediana Δ tok/s STIMATO [min;max fra celle] W=chiaramente peggio (IC95 hi<0) / B=chiaramente meglio (lo>0) / celle\n"); tab("band")
L.append("\n### Controllo ρ=0,26 (P1/P2/P4 = 3 celle/dominio)\n"); tab("ctrl")
L.append("\n### Controllo P4 griglia cost_T_d[T, d_pagato] (1 cella/dominio): Δ [IC95]\n")
L.append("| dominio | variante | "+" | ".join(REFS)+" |"); L.append("|"+"---|"*(2+len(REFS)))
for d in ("code","chat","edit"):
  for a in ARMS:
    L.append("| %s | %s | %s |"%(d,a," | ".join("%+.1f%% [%+.1f;%+.1f] %s"%tuple([x*100 for x in g[d][a+"_vs_"+r]["ci"]]+[g[d][a+"_vs_"+r]["cls"]]) for r in REFS)))
L.append("\n### Draft per round (P4 ρ=0,0992): d del gate / d pagato\n")
for d in ("code","chat","edit"):
  x=c[d+"|P4|rho0.0992"]; L.append("- %s: "%d+", ".join("%s %.2f/%.2f"%(k,x["d_gate_per_round"][k],x["d_charged_per_round"][k]) for k in x["tps_est"]))
print("\n".join(L))
