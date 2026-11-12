from sympy import isprime, factorint, primerange
from math import gcd
from itertools import product
def crt(rs,ms):
    from sympy.ntheory.modular import crt as c
    return int(c(ms,rs)[0])
N=300979369; print(N==7759*38791, (N+1)//2, isprime(7759),isprime(38791))
print(7758*38796==N-1, (N-1)%38790, (N-1)%7758)
q=38791; print(sorted(t for t in range(1,q) if pow(t,5,q)==1))
print(pow(3,N-1,N), pow(3,N-1,N)%4)
# attainable set
def att(N):
    f=factorint(N); imgs=[]; mods=[]
    for p,k in f.items():
        pk=p**k; imgs.append(sorted({pow(b,N-1,pk) for b in range(pk)})) if pk<10**6 else None; mods.append(pk)
    return [crt(list(c),mods) for c in product(*imgs)]
A=att(N); nz=sorted(r for r in A if r); print(len(nz), nz, all(r%2 for r in nz))
def G(N):
    A=att(N); g=N-1
    for r in A:
        if r: g=gcd(g,r-1)
    return g
print(300979369/9439201)
for n in [6601,294409,1024651,1152271,2508013,5444489,5968873,9439201]:
    print(n,factorint(n),G(n))
print(factorint(2752522510861), 627071*4389491)
for n,(a,b) in {429802001:(6911,62191),667081801:(11551,57751),3672754633:(27103,135511)}.items():
    print(n==a*b,isprime(a),isprime(b),(b-1)/(a-1),G(n))
x=894273443482227355; N2=2*x-1; p=1130280271;q2=1582392379
print(N2==p*q2, isprime(p),isprime(q2), N2)
g=226056054; print(p-1==5*g,q2-1==7*g,N2-1==g*(35*g+12),35*g+12,(N2-1)%5)
print(pow(2,N2-1,N2), pow(2,N2-1,N2)%4)
r5=sorted({pow(t,(p-1)//5,p) for t in range(2,60)}); print(r5)
r7=sorted({pow(t,(q2-1)//7,q2) for t in range(2,80)}); print(r7)
print(sorted(t for t in range(1,57751) if pow(t,5,57751)==1))
print(pow(2,328,7),pow(16,328,47))
print((p-1)%(q2-1),(q2-1)%(p-1))
