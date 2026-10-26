import sys; sys.path.insert(0,'.')
from strata_sim.sim2 import *
from strata_sim.synth2 import make_domain
D = make_domain("code", 48, seed=7, session_len=8)
prof = [p for p in base_profiles() if p.name=="P1"][0]
g=GateV2(); c=g.cost; _u=c.update; log=[]
def upd(T,d,k,y):
    b=c.pred(2,1,0); _u(T,d,k,y); a=c.pred(2,1,0)
    if T==2: log.append((len(log),T,d,k,round(y,3),round(b,3),round(a,3)))
c.update=upd; walk(g,D,prof)
for l in log[:25]: print(l)
print(len(log), c.n)
print(c.th.round(3), c.scale, round(c.pred(2,0,7),3), prof.cost(2,0,7), round(c.pred(2,1,0),3))
np.set_printoptions(precision=4, suppress=True, linewidth=200); print(c.P)
x=c.x(2,1,0); Px=c.P@x; print('gain', (Px/(c.lam+x@Px))[1], 'err', 1.809/c.scale - x@c.th)
_u(2,1,0,1.809); print(c.th.round(3))
