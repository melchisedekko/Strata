import json,sys
J=json.load(open(sys.argv[1])); doms=["code","chat","edit"]
def v(src,pn,cand,key):
    bs=[src["%s|%s"%(d,pn)]["pol"][cand][key] for d in doms]
    return sum(b[1]>0 for b in bs), sum(b[2]<0 for b in bs), bs
for cand in ("specu","gate_v2"):
  for key in ("vs_current","vs_cost","vs_k3","vs_specu"):
    if cand=="specu" and key=="vs_specu": continue
    main=[(pn,)+v(J["main"],pn,cand,key)[:2] for pn in ("P1","P2","P4","P4-lo","P4-hi","P1@rhoP4","P2@rhoP4")]
    grid=[v(J["grid"],pn.split("|",1)[1],cand,key)[:2] for pn in [k for k in J["grid"] if k.startswith("code|")]]
    print(cand,key,"main:",main)
    print("   grid ok %d/%d, any clearly-neg domain in %d"%(sum(p>=2 and n==0 for p,n in grid),len(grid),sum(n>0 for p,n in grid)))
