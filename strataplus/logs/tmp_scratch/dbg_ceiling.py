import sys, runpy
sys.path.insert(0,"/workspace/strata-policy/replay")
sys.argv=["x","/tmp/dbg_ceiling_out"]
src=open("ceiling_third_source.py").read().split("P4 = load_p4")[0].replace("os.path.dirname(os.path.abspath(__file__))","\"/workspace/strata-policy/replay\"")
exec(compile(src,"c","exec"))
R=load_tf(FILES["holdout_code"]); PR,_=prompts(FILES["holdout_code"])
tot=0
for q in R[:30]:
    seq=list(PR[q["req"]])+q["y"].tolist(); sx=Suffix(seq); lo=0; plen=len(PR[q["req"]]); y=q["y"].tolist()
    ng=NgramMod(n_min=1)
    ng.begin(seq,0,plen)
    for i in range(q["n"]):
        N=plen+i; ps=sx.propose(N,0); pn=ng.draft(seq,0,N)
        a_s=lcp(ps,y,i); a_n=lcp(pn,y,i); am=int(q["mtp_acc"][i]); al=int(q["lk_acc"][i])
        if max(a_s,a_n)>max(am,al):
            tot+=1
            if tot<8: print(q["req"],i,q["n"],"mtp",am,"lk",al,"lk_k",int(q["lk_k"][i]),"sfx",a_s,len(ps),"ng",a_n,len(pn))
print("rounds where third>max",tot)
import numpy as np
print("mean mtp_acc",np.mean([q["mtp_acc"].mean() for q in R]),"share mtp=7",np.mean([ (q["mtp_acc"]==7).mean() for q in R]))
