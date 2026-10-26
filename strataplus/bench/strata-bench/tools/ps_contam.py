import sys,re
f,tag=sys.argv[1],sys.argv[2]; snaps=bad=0; cur=hit=False; procs=set()
for l in open(f):
    if l.startswith('== '):
        if cur and hit: bad+=1
        cur=('DURING '+tag) in l and l.rstrip().endswith(tag); hit=False; snaps+=cur; continue
    if cur:
        x=l.split()
        if len(x)>4 and re.match(r'^[\d.]+$',x[1]) and float(x[1])>50 and 'llama_spec_trace' not in l and 'ps -eo' not in l: hit=True; procs.add(' '.join(x[4:])[:60])
if cur and hit: bad+=1
print(tag,'snapshots',snaps,'with_foreign>50%',bad,sorted(procs))
