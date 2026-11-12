from sympy import factorint, isprime, primerange, gcd, totient, mod_inverse, Rational, sqrt, sin, pi, N as NN, nsimplify
from math import gcd as g
from itertools import product
from functools import reduce

def resid_sets(N):
    f = factorint(N); sets=[]
    for p,k in f.items():
        m=p**k
        img={pow(b,N-1,m) for b in range(1,m) if b%p}
        sets.append((m, img|{0}))
    return sets
def G(N, limit=10**7):
    sets=resid_sets(N); mods=[m for m,_ in sets]
    # CRT basis
    es=[]
    for m in mods:
        c=N//m; es.append(c*mod_inverse(c,m)%N)
    cur=0; size=1
    for _,s in sets: size*=len(s)
    assert size<=limit, size
    for combo in product(*[sorted(s) for _,s in sets]):
        r=sum(e*x for e,x in zip(es,combo))%N
        if r: cur=g(cur,r-1)
        if cur==1: return 1
    return cur
def carm(N):
    f=factorint(N)
    return len(f)>=2 and all(k==1 for k in f.values()) and all((N-1)%(p-1)==0 for p in f)
def class_miss(N):
    sets=resid_sets(N); mods=[m for m,_ in sets]; es=[]
    for m in mods:
        c=N//m; es.append(c*mod_inverse(c,m)%N)
    for combo in product(*[sorted(s) for _,s in sets]):
        r=sum(e*x for e,x in zip(es,combo))%N
        if r and (r%4==3 or r%4==(N-1)%4): return False
    return True
print("300979369", factorint(300979369), 1+5*7758, 7759%8, "G=",G(300979369), "carm",carm(300979369))
for N,M in [(6601,2),(9439201,6),(2508013,4),(4034969401,5),(710382401,8),(6196188961,13)]:
    print(N, factorint(N), "carm",carm(N), "G",G(N), "M|G", G(N)%M==0)
print("561",factorint(561),carm(561),G(561),totient(561),totient(6601))
print("36953929",factorint(36953929),1+5*2718,carm(36953929),"G",G(36953929),"classmiss",class_miss(36953929))
print("2508013 classmiss",class_miss(2508013))
print("9439201 classmiss",class_miss(9439201))
print("300979369 classmiss",class_miss(300979369))
# j=3 family
bad=[p for p in primerange(3,20000) if isprime(3*p-2) and G(p*(3*p-2))!=1]
print("j=3 members with G>1 (p<2e4):",bad)
# delta: volume of {1/2<=x1+x2+x3<=5/4} in [0,3/4]^3
from sympy import symbols
import itertools
def vol_le(s,a=Rational(3,4)):
    # volume of {x in [0,a]^3: sum<=s} by inclusion-exclusion
    from sympy import binomial, factorial
    tot=0
    for k in range(4):
        t=s-k*a
        if t>0: tot+=(-1)**k*binomial(3,k)*t**3/6
    return tot
v=vol_le(Rational(5,4))-vol_le(Rational(1,2))
print("abs vol",v,"cube",Rational(27,64),"rel",v/Rational(27,64))
print("31/4096",31/4096, "348/45126",348/45126, "334/45127",334/45127)
lam=1/(12*sin(pi/8)**2); print("lambda",NN(lam), "15/26",15/26,"1-lam",NN(1-lam),"11/26",11/26)
import cmath
F=lambda n,t: abs(sum(cmath.exp(2j*cmath.pi*k*t) for k in range(n+1)))**2/(n+1)
print("F11(1/8)",F(11,1/8), "max F11 on [1/8,1/2]", max(F(11,1/8+i*(3/8)/20000) for i in range(20001)))
print("sum c_k", sum(Rational(2*(12-k),12) for k in range(1,12)))
