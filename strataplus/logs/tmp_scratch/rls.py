import sys; sys.path.insert(0,'.'); import numpy as np
from strata_sim.sim2 import CostRLS, base_profiles
prof=[p for p in base_profiles() if p.name=="P1"][0]
rng=np.random.default_rng(0); c=CostRLS()
for n in range(20000):
    T=int(rng.integers(1,5)); d=max(T-1,int(rng.integers(0,4))) if rng.random()<0.5 else T-1; k=int(rng.integers(0,8))
    c.update(T,d,k,prof.cost(T,d,k))
print([round(c.pred(T,T-1,0),3) for T in range(1,6)], [round(prof.cost(T,T-1,0),3) for T in range(1,6)])
# only-diagonal data as in practice (MTP rounds T=d+1, none rounds with d drafted)
c=CostRLS()
for n in range(20000):
    d=int(rng.integers(1,4)); T=1 if rng.random()<0.3 else int(rng.integers(2,d+2)); k=int(rng.integers(0,8))
    c.update(T,d,k,prof.cost(T,d,k))
print([round(c.pred(T,T-1,0),3) for T in range(1,6)], [round(prof.cost(T,T-1,0),3) for T in range(1,6)], c.th.round(3))
