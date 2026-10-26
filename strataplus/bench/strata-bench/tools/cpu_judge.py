#!/usr/bin/env python3
"""Giudizio di un log cpu_foreign: stampa 'nb max' = intervalli con carico estraneo >=0.5 core (esclusa infrastruttura sand-host) e massimo.
Log v1 (senza colonna infra): una riga e' attribuita a sand-host solo se il processo top e' sand-host e (totale - top) < 0.5."""
import sys
nb = 0; mx = 0.0
for l in open(sys.argv[1]):
    f = l.split()
    if len(f) < 2: continue
    x = float(f[1])
    if len(f) > 2 and not f[2].startswith('infra=') and '/opt/sand/sand-host/host' in l and len(f) > 3: x = x - float(f[2])
    mx = max(mx, x); nb += x >= 0.5
print(nb, round(mx, 3))
