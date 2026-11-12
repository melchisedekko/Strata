from sympy import isprime, factorint, gcd, symbols, expand, simplify, primerange
from math import log, lcm, isqrt
from functools import reduce
rows=[(7,60,29,6486240,7359698031169821895224001),
(8,420,209,23601123000,121743572279260616337106970304278490001),
(11,5040,419,1094162424600,97048940404974711363791828287812695521836001),
(13,27720,4619,854021634025560,61423212019676954455426453373083752772573891910374548001),
(17,6486480,360359,28475431726698356400,None),(19,110270160,12252239,5985917979608424412114560,None),(23,931170240,232792559,27104577797036681065696572000,None)]
def lnd(G):
    M=2
    while G%M==0: M+=1
    return M
for l,G,m,K,Nt in rows:
    P,Q,R=m*K+1,(m+1)*K+1,(m+2)*K+1; N=P*Q*R
    ok = all(isprime(x) for x in (P,Q,R))
    kors = all((N-1)%(x-1)==0 for x in (P,Q,R))
    cond = (2*K+3)%m==0 and K%(m+1)==0 and (2*K+2*m+1)%(m+2)==0
    vP=(P-m*m)//2; vQ=(m+1)**2; vR=(R-(m+2)**2)//2
    g=reduce(gcd,[vP,vQ,vR])
    print(l, ok, kors, cond, m%2, K%2, K>=m+3, g==G, lnd(G)==l, (Nt==N) if Nt else '-', len(str(N)), N.bit_length()-1, "lnN/lnL=%.2f"%(log(N)/log(reduce(lcm,range(1,l)))), "lcm=",reduce(lcm,range(1,l)), "G==lcm",G==reduce(lcm,range(1,l)))
    print("  P,Q,R",P,Q,R, "vP,vR",vP,vR)
    if l==7: print("  divs", (2*K+3)//m,K//30,(2*K+2*m+1)//31, (2*K+3)%m)
    if l==8: print("  divs", (2*K+3)/m,K/210,(2*K+2*m+1)/211)
# row-1 N details
N=rows[0][4]; print("row1 log2 N(N-1)", (N*(N-1)).bit_length()-1)
N2=rows[1][4]; print("row2 2^126<=N<2^127", 2**126<=N2<2**127)
# divisors of 60
print([d for d in range(1,61) if 60%d==0])
# algebra
m,K=symbols('m K')
P,Q,R=m*K+1,(m+1)*K+1,(m+2)*K+1
W=m*(m+1)*(m+2)*K**2+(3*m**2+6*m+2)*K+3*(m+1)
print("PQR-1-KW", expand(P*Q*R-1-K*W))
print("Kcoef", expand(2*m**3+3*m**2-4*(m+1)**3+(m+2)**2*(2*m+1)))
D=m**2*Q*R-2*(m+1)**2*P*R+(m+2)**2*P*Q; print("D",expand(D))
print("QR", expand(Q*R-((m+1)*(m+2)*K**2+(2*m+3)*K+1)), expand(P*R-(m*(m+2)*K**2+2*(m+1)*K+1)), expand(P*Q-(m*(m+1)*K**2+(2*m+1)*K+1)))
M,Kp=symbols('M Kp')
print(expand((2*M-1)*2*M*Kp+1-(2*M-1)**2-2*M*((2*M-1)*Kp-2*M+2)), expand((2*M+1)*2*M*Kp+1-(2*M+1)**2-2*M*((2*M+1)*Kp-2*M-2)))
L=symbols('L'); mm=2*L-1
print(expand(mm*2*L*Kp+1-mm**2-2*L*(mm*Kp-mm+1)), expand((mm+2)*2*L*Kp+1-(mm+2)**2-2*L*((mm+2)*Kp-(mm+3))))
# sec 8 example
S=29*30*31; print(S, 6486240-240*S, 13440%30, (2*13440+3)%29, (2*13440+59)%31, isprime(389761), 29*13440+1, factorint(403201), factorint(416641), isqrt(389761))
print([2*reduce(lcm,range(1,B+1))-1 for B in range(1,7)])
print("909",(13+30)*7*3, 172*7, [9*B*B-12*B-10 for B in (2,3)], 4+12*2, 8*4)
# census N
p,q,r=7757611,20686961,618022931; N=p*q*r
print(N==99181182856782173431201, all(isprime(x) for x in (p,q,r)), all((N-1)%(x-1)==0 for x in (p,q,r)), "%.2f %.2f"%(log(N),log(N)/log(420)), (p-1)%839,(q-1)%840,(r-1)%841)
# G via idempotents
from sympy.ntheory.modular import crt
ps=[p,q,r]; import itertools
vals=[]
for T in itertools.product([0,1],repeat=3):
    if sum(T)==0: continue
    e=crt(ps,list(T))[0]; vals.append(e-1)
g=reduce(gcd,vals); print("G census",g, lnd(g))
c=cert=6309744080195907196223714244800892001
print(isprime(c), 2**122<=c<2**123, len(str(c)))
# digit range of last nine factors
fs=[]
for l,G,m,K,Nt in rows[4:]:
    fs+= [m*K+1,(m+1)*K+1,(m+2)*K+1]
print(sorted(len(str(x)) for x in fs), max(fs)<2**128)
print("2.1e8", 201073441<2.1e8)
