import sys,struct,urllib.request
url=sys.argv[1]
def get(a,b):
    r=urllib.request.Request(url,headers={"Range":f"bytes={a}-{b}"}); return urllib.request.urlopen(r).read()
buf=get(0,16*1024*1024-1); p=0
def rd(fmt):
    global p; v=struct.unpack_from("<"+fmt,buf,p); p+=struct.calcsize("<"+fmt); return v[0]
def rs():
    global p; n=rd("Q"); s=buf[p:p+n].decode("utf8","replace"); p+=n; return s
assert buf[:4]==b"GGUF"; p=4; ver=rd("I"); nt=rd("Q"); nkv=rd("Q")
sz={0:"B",1:"b",2:"H",3:"h",4:"I",5:"i",6:"f",7:"?",10:"Q",11:"q",12:"d"}
kv={}
def val(t):
    if t==8: return rs()
    if t==9:
        at=rd("I"); n=rd("Q"); out=[val(at) for _ in range(n)]; return out if n<8 else f"[array len {n}]"
    return rd(sz[t])
for _ in range(nkv):
    k=rs(); t=rd("I"); kv[k]=val(t)
names=[]
for _ in range(nt):
    n=rs(); nd=rd("I"); [rd("Q") for _ in range(nd)]; rd("I"); rd("Q"); names.append(n)
print("arch",kv.get("general.architecture"),"n_tensors",nt)
for k,v in kv.items():
    if any(x in k for x in ("nextn","mtp","block_count","license","vocab_size")) or k.endswith("tokens"): print(" kv",k,v)
mt=[n for n in names if any(x in n for x in ("nextn","mtp"))]
blk=sorted({int(n.split(".")[1]) for n in names if n.startswith("blk.")})
print(" max blk",blk[-1]," mtp/nextn tensors:",len(mt), mt[:6])
print(" tensors of last blk:",[n for n in names if n.startswith(f"blk.{blk[-1]}.")][:20])
