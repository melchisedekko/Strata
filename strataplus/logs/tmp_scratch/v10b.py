from sympy import primerange, divisors, primitive_root
from fractions import Fraction
import itertools
best=(0,0)
for q in primerange(3,20000):
    g=primitive_root(q)
    for s in divisors(q-1):
        if s%2==0 or s==1: continue
        h=pow(g,(q-1)//s,q)
        H=[pow(h,i,q) for i in range(s)]
        k=(q-1)//s
        fail=False
        for i in range(k):
            u=pow(g,i,q)
            if all((u*x)%q > q/2 for x in H) : fail=True;break
        if fail and s>best[0]: best=(s,q)
print(best)
print(348/45126)
# volume of {x in [0,3/4]^3 : 1/2<=sum<=5/4}
import sympy as sp
def vol_le(t,a=Fraction(3,4),n=3):
    # volume of {x in [0,a]^n: sum<=t} by inclusion-exclusion
    from math import comb, factorial
    v=Fraction(0)
    for k in range(n+1):
        r=t-k*a
        if r>0: v+=(-1)**k*comb(n,k)*r**n/factorial(n)
    return v
V=vol_le(Fraction(5,4))-vol_le(Fraction(1,2)); print(V, V/Fraction(27,64))
