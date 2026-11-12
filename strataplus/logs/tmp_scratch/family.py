from sympy import primerange, isprime
from math import gcd
def residues(p,q):
    N=p*q
    ep=q*pow(q,-1,p)%N; eq=p*pow(p,-1,q)%N
    h=2
    while pow(h,(q-1)//5,q)==1: h+=1
    z=pow(h,(q-1)//5,q); Sq=[pow(z,i,q) for i in range(5)]
    assert len(set(Sq))==5
    out=[]
    for x in (0,1):
        for y in [0]+Sq:
            r=(ep*x+eq*y)%N
            if r: out.append(r)
    return N,out
# sanity on the running example: compare with brute force image for small b
N,rs=residues(7759,38791)
assert all(pow(b,N-1,38791) in {r%38791 for r in rs} for b in range(1,200) if b%38791)
mem=0; blind=0; miss=0; cls={1:0,3:0,5:0,7:0}; blind7=0
for p in primerange(3,6_000_000):
    q=5*p-4
    if not isprime(q): continue
    mem+=1; cls[p%8]+=1
    N,rs=residues(p,q)
    Gv=0
    for r in rs: Gv=gcd(Gv,r-1)
    if Gv>1:
        blind+=1; blind7 += (p%8==7)
    miss += not any(r%4==3 or r%4==(N-1)%4 for r in rs)
print("members p<6e6",mem,"G>1",blind,"p=7mod8 among them",blind7,"classmiss",miss)
print("mod8",cls,{k:round(v/mem,4) for k,v in cls.items()})
cnt=sum(1 for p in primerange(3,6_000_002) if 5*p-4<3*10**7 and isprime(5*p-4))
print("members q<3e7",cnt)
