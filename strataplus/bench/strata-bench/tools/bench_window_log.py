import re,time,os
C='/workspace/strata-plus/traces/raw/v11/campaign.log';O='/workspace/strata-plus/cpu_busy_bench.log'
f=open(C);f.seek(0,2);st={}
while True:
  l=f.readline()
  if not l: time.sleep(5); continue
  m=re.match(r'(\S+ \S+) CET (START|END) (\S+)(?: att (\d+))?(.*)',l.strip())
  if not m: continue
  k=(m[3],m[4])
  if m[2]=='START': st[k]=(m[1],m[5].strip()); open(O,'a').write(f"{m[1]} | (in corso) | START {m[3]}{' att '+m[4] if m[4] else ''} {m[5].strip()} (strata-bench) |\n")
  elif k in st:
    s,d=st.pop(k); open(O,'a').write(f"{s} | {m[1]} | {m[3]}{' att '+m[4] if m[4] else ''} {d} (strata-bench, 1 processo llama) | {m[5].strip()[:140]}\n")
