import json,collections,sys
for f in sys.argv[1:]:
  rq={};sc=collections.Counter();last={};bad=[]
  for l in open(f):
    j=json.loads(l)
    if j['type']=='round': sc[(j['req_id'],j.get('rep',0))]+=j['committed']; last[(j['req_id'],j.get('rep',0))]=j
    if j['type']=='request': rq[(j['req_id'],j.get('rep',0))]=j['output_tokens']
  for k,v in rq.items():
    if sc[k]>v: bad.append((k[0],sc[k],v,last[k]['pos'],last[k]['committed'],last[k]['accepted']))
  print(f.split('/')[-1],len(rq),bad)
