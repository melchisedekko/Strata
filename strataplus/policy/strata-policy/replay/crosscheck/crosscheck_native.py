"""Python port vs production library through ctypes (same random op streams as crosscheck.py)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from crosscheck import stream
from strata_sim.draft_policy_port import DraftPolicy
from strata_sim.native import NativeDraftPolicy

def run(pol, ops):
    res = []
    for o in ops:
        if o[0] == "R": pol.robust = bool(o[1])
        elif o[0] == "X": pol.set_context(o[1])
        elif o[0] == "C": l, t = pol.choose(o[1], o[2], o[3]); res.append((int(l), t))
        elif o[0] == "O": pol.observe(bool(o[1]), o[2], o[3], o[4], o[5])
        elif o[0] == "P": pol.observe_probs([float(np.float32(v)) for v in o[2]], o[1], o[3])
        elif o[0] == "K": res.append(pol.mtp_chain_rows([float(np.float32(v)) for v in o[3]], o[1]))
    return res

bad = tot = 0
for seed in range(40):
    ops = stream(seed)
    a, b = run(DraftPolicy(6), ops), run(NativeDraftPolicy(6), ops)
    tot += len(a); bad += a != b
print(f"crosscheck native(ctypes) vs port: {tot} answers, {bad} mismatching streams"); sys.exit(1 if bad else 0)
