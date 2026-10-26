import json,collections,sys
f=sys.argv[1]
req={};rounds=collections.defaultdict(list)
for l in open(f):
  j=json.loads(l)
  if j['type']=='round': rounds[j['req_id']].append(j)
  elif j['type']=='request': req[j['req_id']]=j
agg=collections.defaultdict(lambda:[0,0,0,0]); nclamp=0
for k,j in req.items():
  dv=j['first_divergence_pos']; lim=dv if dv is not None else 10**9; L=j['output_tokens']
  for r in rounds[k]:
    c=min(r['accepted']+1, L-r['pos']); nclamp+= c<r['accepted']+1
    for g in (j['domain'],'ALL'):
      A=agg[g]; A[0]+=c; A[1]+=1
      if r['pos']+min(r['committed'],L-r['pos'])<=lim: A[2]+=c; A[3]+=1
print(f.split('/')[-1],'clamped_rounds',nclamp,{g:(round(a[0]/a[1],4),a[1],round(a[2]/a[3],4),a[3]) for g,a in sorted(agg.items())})
