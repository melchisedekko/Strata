import json,sys,collections
EOG={248044,248046,248063,248064,248065}
for f in sys.argv[1:]:
    bad=collections.Counter(); rounds=0; prompts=set(); kinds=collections.Counter()
    for line in open(f):
        r=json.loads(line)
        if r.get("type")!="round": continue
        rounds+=1; p=r["req_id"]; prompts.add(p)
        tt=r["target_tokens"]; vm=r["vmargin"]; prop=r["proposal"]; acc=r["accepted"]; com=r["committed"]
        err=[]
        # argmax check: each target token must be top-1 of its verify row
        for j,t in enumerate(tt):
            if j>=len(vm) or vm[j][0]!=t: err.append("not_argmax")
        # accepted = longest prefix match of proposal vs target, stopping after EOG
        a=0
        while a<len(prop) and a<len(tt) and prop[a]==tt[a]:
            a+=1
            if prop[a-1] in EOG: break
        if a!=acc: err.append("accepted_mismatch")
        if com>len(tt) or com>acc+1: err.append("committed_mismatch")
        for e in set(err): kinds[e]+=1
        if err: bad[p]+=1
    print(f, "rounds",rounds,"prompts",len(prompts),"bad_rounds",sum(bad.values()),"bad_prompts",len(bad),dict(kinds))
