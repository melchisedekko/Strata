import json, sys, collections
sys.path.insert(0,'/workspace/strata-policy/replay')
from strata_sim.postprocess import load_tf
def keys(path):
    K=collections.defaultdict(set); reps=collections.Counter(); types=collections.Counter(); bad=0
    for line in open(path):
        line=line.strip()
        if not line: continue
        try: o=json.loads(line)
        except Exception: bad+=1; continue
        t=o.get("type"); types[t]+=1; reps[o.get("rep",0)]+=1; K[t]|=set(o)
        if t=="round":
            K["cand"]|=set(o.get("cand",{})); K["cand.mtp"]|=set(o.get("cand",{}).get("mtp",{}))
    return K,reps,types,bad
for path in sys.argv[1:]:
    K,reps,types,bad=keys(path); R=load_tf(path)
    dom=collections.Counter(r["domain"] for r in R); nr=sum(r["n"] for r in R); mm=sum(r["target_mismatch"] for r in R)
    sess=collections.Counter(r["session"] for r in R)
    print(path); print(" types",dict(types),"reps",dict(reps),"json_bad",bad)
    print(" loaded reqs",len(R),"per dom",dict(dom),"rounds",nr,"target_mismatch",mm,"sessions",len(sess),"max req/session",max(sess.values()))
    for k,v in K.items(): print("  keys",k,sorted(v))
