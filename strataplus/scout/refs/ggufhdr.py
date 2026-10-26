import struct,sys,collections
f=open(sys.argv[1],'rb'); r=lambda fmt: struct.unpack('<'+fmt, f.read(struct.calcsize('<'+fmt)))
magic=f.read(4); ver,=r('I'); nt,=r('Q'); nkv,=r('Q')
def s(): n,=r('Q'); return f.read(n).decode('utf8','replace')
SZ={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
def val(t):
    if t==8: return s()
    if t==9:
        at,=r('I'); n,=r('Q'); return [val(at) for _ in range(n)] if n<64 else (f.seek(0,1), [val(at) for _ in range(n)])[1][:3]+['...%d'%n]
    return r(SZ[t])[0]
kv={}
for _ in range(nkv):
    k=s(); t,=r('I'); kv[k]=val(t)
for k in kv:
    if 'token' not in k: print(k,'=',kv[k])
TN={0:'F32',1:'F16',2:'Q4_0',3:'Q4_1',6:'Q5_0',7:'Q5_1',8:'Q8_0',10:'Q2_K',11:'Q3_K',12:'Q4_K',13:'Q5_K',14:'Q6_K',30:'BF16'}
cnt=collections.Counter()
for _ in range(nt):
    n=s(); nd,=r('I'); dims=r('Q'*nd); t,=r('I'); off,=r('Q')
    typ=TN.get(t,str(t)); cnt[typ]+=1
    if typ not in ('Q4_K',) or 'blk.0.' in n or 'blk.3.' in n or 'mtp' in n or 'nextn' in n or 'blk.24' in n or 'output' in n or 'token' in n:
        print(n,dims,typ)
print(cnt)
