#!/usr/bin/env python3
"""Serie del carico estraneo (core) per intervallo, stessa regola di cpu_judge.py; stampa i valori separati da spazio."""
import sys
v = []
for l in open(sys.argv[1]):
    f = l.split()
    if len(f) < 2: continue
    x = float(f[1])
    if len(f) > 2 and not f[2].startswith('infra=') and '/opt/sand/sand-host/host' in l and len(f) > 3: x = x - float(f[2])
    v.append(round(x, 3))
print(' '.join(map(str, v)))
