import sys; sys.path.insert(0,'.')
from strata_sim.sim2 import *
from strata_sim.synth2 import make_domain
D = make_domain("code", 48, seed=7, session_len=8)
prof = [p for p in base_profiles() if p.name=="P1"][0]
g=GateV2(); c=g.cost; _u=c.update; k=[0]
def upd(T,d,kk,y):
    if T==2 and k[0]<6:
        x=c.x(T,d,kk); Px=c.P@x; th0=c.th.copy(); _u(T,d,kk,y); k[0]+=1
        print('P11',round(c.P[1,1]+0,4),'gain',round((Px/(c.lam+x@Px))[1],4),'th1',round(th0[1],3),'->',round(c.th[1],3),'th0',round(c.th[0],3))
    else: _u(T,d,kk,y)
c.update=upd; walk(g,D[:5],prof)
