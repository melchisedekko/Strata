from sympy import primerange, divisors, primitive_root
res=[]
for q in primerange(3,20000):
    g=primitive_root(q)
    for s in [15]:
        if (q-1)%s: continue
        h=pow(g,(q-1)//s,q); H=[pow(h,i,q) for i in range(s)]
        for i in range((q-1)//s):
            u=pow(g,i,q)
            if all((u*x)%q > q/2 for x in H): res.append(q);break
print(res)
