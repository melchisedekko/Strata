import numpy as np
def count(X):
    s=np.ones(X+1,dtype=bool); s[:2]=False; s[4::2]=False
    for i in range(3,int(X**0.5)+1,2):
        if s[i]: s[i*i::2*i]=False
    primes=np.nonzero(s)[0]
    oddp=len(primes)-1
    pp=0
    for p in primes[1:]:
        p=int(p)
        if p*p>X: break
        v=p*p
        while v<=X: pp+=1; v*=p
    odd=(X+1)//2  # odd numbers 1..X
    comp_all=odd-1-oddp
    return comp_all, comp_all-pp
print("3.1e8 (all odd composites, omega>=2):",count(310_000_000))
print("4e8:",count(400_000_000))
