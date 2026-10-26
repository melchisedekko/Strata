#!/usr/bin/env python3
"""Carico CPU (v2: colonna 3 infra=carico di /opt/sand/sand-host/host, escluso dalla colonna 2) dei processi "estranei" (tutti tranne llama_spec_trace* e questo monitor) da delta di /proc/<pid>/stat (utime+stime).
wait <secs> <thr_cores> [timeout_s]: esce 0 quando il carico estraneo resta < thr per <secs> secondi consecutivi (campioni 1 s).
monitor <file> [interval_s]: scrive ogni intervallo 'ts foreign_cores top_proc' finche' non viene ucciso."""
import os, sys, time
HZ = os.sysconf('SC_CLK_TCK'); ME = os.getpid()
def snap():
    d = {}
    for p in os.listdir('/proc'):
        if not p.isdigit() or int(p) == ME: continue
        try:
            st = open(f'/proc/{p}/stat').read(); cmd = open(f'/proc/{p}/cmdline', 'rb').read().replace(b'\0', b' ').decode(errors='replace')[:80]
        except OSError: continue
        if 'llama_spec_trace' in cmd or 'cpu_foreign.py' in cmd: continue
        f = st[st.rfind(')') + 2:].split(); d[p] = (int(f[11]) + int(f[12]), cmd)
    return d
INFRA = ('/opt/sand/sand-host/host',)   # infrastruttura del box (non controllabile), registrata a parte, esclusa dal criterio dalle 05:05 CET
def load(a, b, dt, infra=False):
    tot = 0; inf = 0; top = (0, '')
    for p, (t, c) in b.items():
        if p in a:
            x = (t - a[p][0]) / HZ / dt
            if any(k in c for k in INFRA): inf += x; continue
            tot += x; top = max(top, (x, c))
    return (tot, top, inf) if infra else (tot, top)
if sys.argv[1] == 'wait':
    secs, thr = float(sys.argv[2]), float(sys.argv[3]); to = float(sys.argv[4]) if len(sys.argv) > 4 else 3600
    t0 = time.time(); ok = 0; a = snap(); ta = time.time()
    while time.time() - t0 < to:
        time.sleep(1); b = snap(); tb = time.time(); x, top = load(a, b, tb - ta); a, ta = b, tb
        ok = ok + 1 if x < thr else 0
        if ok >= secs: print(f'free after {time.time()-t0:.0f}s'); sys.exit(0)
    print('timeout'); sys.exit(1)
else:
    out = open(sys.argv[2], 'a', buffering=1); iv = float(sys.argv[3]) if len(sys.argv) > 3 else 2
    a = snap(); ta = time.time()
    while True:
        time.sleep(iv); b = snap(); tb = time.time(); x, top, inf = load(a, b, tb - ta, True); a, ta = b, tb
        out.write(f'{time.strftime("%T")} {x:.3f} infra={inf:.3f} {top[0]:.2f} {top[1]}\n')
