import sys; sys.path.insert(0,'.')
from strata_sim.sim2 import *
from strata_sim.postprocess import load_tf
R=load_tf('/workspace/strata-plus/traces/tf_d7.jsonl'); P4=load_p4()
for sn,s in (("P1",S_P1),("P2",p2_s()),("P4",P4.s)):
  prof=Profile(sn,s,0.0992,P4.rho_lu,"x")
  for d in ("chat","code"):
    reqs=[r for r in R if r["domain"]==d]; cl=[q["session"] for q in reqs]
    rc=walk(StrataCurrent(spec_cost=True),reqs,prof); sc=summarize(rc,prof)
    out=[]
    for nm,p in (("c_nolookup",SpecuC(min_match=10**6)),("c_m12",SpecuC(min_match=12)),("gate_ref",GateV2()),("gate_t5",GateV2(tmax=5))):
      r=walk(p,reqs,prof); b=boot_ratio(rc,r,cl); s2=summarize(r,prof)
      out.append("%s %+.1f%% [%+.1f,%+.1f] none=%.0f%% lk=%.0f%% dm=%.2f"%(nm,100*b[0],100*b[1],100*b[2],100*s2['src_share']['none'],100*s2['src_share']['lk'],s2['dm_per_round']))
    print(sn,d,"SPEC_COST none=%.0f%% lk=%.0f%% dm=%.2f"%(100*sc['src_share']['none'],100*sc['src_share']['lk'],sc['dm_per_round']),"|"," | ".join(out))
