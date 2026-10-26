import json,statistics as st,sys
o=json.load(open('holdout_v11/holdout_v11.json')); n=json.load(open('holdout_v11_fulldraft/holdout_v11_fulldraft.json'))
f=lambda x:"%+.1f [%+.1f, %+.1f]"%tuple(100*v for v in x["ci"])
L=[]; S={}
for arm in "AB":
  for V in ("V1","V2"):
    L.append("\n### Braccio %s — costo %s (modello additivo; fascia ρ primaria, ρ=0,26 controllo)\n"%(arm,V))
    L.append("| cella | vs default PRIMA | vs default DOPO | vs SPEC_COST PRIMA | vs SPEC_COST DOPO | vs k=3 DOPO |")
    L.append("|---|---|---|---|---|---|")
    oc=o["versions"][V]["cells"]; nc=n["additive"][V]["cells"]
    for k in sorted(oc, key=lambda k:(["code","chat","edit"].index(k.split("|")[0]),k)):
      a,b=oc[k],nc[k]
      tag=" (controllo)" if "0.2600" in k else ""
      L.append("| %s%s | %s %s | %s %s | %s %s | %s %s | %s %s |"%(k,tag,f(a[arm+"_vs_default"]),a[arm+"_vs_default"]["cls"],f(b[arm+"_vs_default"]),b[arm+"_vs_default"]["cls"],
        f(a[arm+"_vs_spec_cost"]),a[arm+"_vs_spec_cost"]["cls"],f(b[arm+"_vs_spec_cost"]),b[arm+"_vs_spec_cost"]["cls"],f(b[arm+"_vs_k3"]),b[arm+"_vs_k3"]["cls"]))
    # summaries band only
    for ref in ("default","spec_cost","k3"):
      for d in ("code","chat","edit"):
        ks=[k for k in oc if k.startswith(d+"|") and "0.2600" not in k]
        dl=[100*(nc[k][arm+"_vs_"+ref]["ci"][0]-oc[k][arm+"_vs_"+ref]["ci"][0]) for k in ks]
        af=[100*nc[k][arm+"_vs_"+ref]["ci"][0] for k in ks]
        wb=sum(oc[k][arm+"_vs_"+ref]["cls"]=="worse" for k in ks); wa=sum(nc[k][arm+"_vs_"+ref]["cls"]=="worse" for k in ks)
        ba=sum(nc[k][arm+"_vs_"+ref]["cls"]=="better" for k in ks)
        S[(arm,V,ref,d)]=dict(med_delta=st.median(dl),dmin=min(dl),dmax=max(dl),after_med=st.median(af),after_min=min(af),after_max=max(af),worse_before=wb,worse_after=wa,better_after=ba,n=len(ks))
L2=["\n## Sintesi per dominio (solo fascia ρ 0,059–0,1394, 15 celle per dominio = P1/P2/P4 × 5 ρ)\n",
    "Δ = punto DOPO − punto PRIMA, in punti percentuali di guadagno tok/s STIMATO.\n",
    "| braccio | costo | rif. | dominio | Δ mediana (pp) | Δ range (pp) | guadagno DOPO mediana (range) | celle nettamente peggiori prima→dopo | celle nettamente migliori dopo |","|---|---|---|---|---|---|---|---|---|"]
for (arm,V,ref,d),s in S.items():
  L2.append("| %s | %s | %s | %s | %+.1f | %+.1f … %+.1f | %+.1f%% (%+.1f … %+.1f) | %d → %d / %d | %d / %d |"%(arm,V,ref,d,s["med_delta"],s["dmin"],s["dmax"],s["after_med"],s["after_min"],s["after_max"],s["worse_before"],s["worse_after"],s["n"],s["better_after"],s["n"]))
G=["\n## Griglia P4 misurata (cost_T_d di cost_p4_cpu.json, d=0..8; identica in V1 e V2), tutte le policy con la stessa griglia\n",
   "PRIMA = cost_T_d[T, d scelta dalla policy]; DOPO = cost_T_d[T, d che il motore calcola] (A d=4, B d=7; baseline invariati perché già fedeli). Nota: la griglia contiene mtp_process(T) solo se d>0 e un ρ effettivo ~0,27–0,32/draft (lm_head a vocabolario pieno): leggere come controllo, non fascia primaria.\n",
   "| braccio | dominio | vs default PRIMA | DOPO | vs SPEC_COST PRIMA | DOPO | vs k=3 PRIMA | DOPO |","|---|---|---|---|---|---|---|---|"]
for arm in "AB":
  for d in ("code","chat","edit"):
    b,a=n["grid"]["before"][d],n["grid"]["after"][d]
    G.append("| %s | %s | %s %s | %s %s | %s %s | %s %s | %s %s | %s %s |"%(arm,d,*sum([[f(x[arm+"_vs_"+r]),x[arm+"_vs_"+r]["cls"]] for r in ("default","spec_cost","k3") for x in (b,a)],[])))
json.dump({"%s|%s|%s|%s"%k:v for k,v in S.items()},open('holdout_v11_fulldraft/summary_band.json','w'),indent=1)
open('/tmp/jg/tables.md','w').write("\n".join(L2+G+["\n## Tabelle complete per cella (IC95 = boot_ratio a cluster sulle sessioni, B=2000, seed 0)"]+L))
for x in L2+G: print(x)
