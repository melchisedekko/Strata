import sys, os
sys.path.insert(0, "/workspace/strata-policy/replay"); sys.path.insert(0, "/workspace/strata-policy/replay/tests")
import strata_sim.sim2 as S
S.P3_LIB = sys.argv[1]
import test_joint_gate_parity as T
from strata_sim.postprocess import load_tf
from strata_sim.sim2 import GateV2, GateV2Native, load_p4, S_P1, p2_s, Profile
bad = T.main()
# tf_d7 parity, arms A/B, band centre + control
R = load_tf("/workspace/strata-plus/traces/tf_d7.jsonl"); P4 = load_p4()
for sn, s in (("P1", S_P1), ("P2", p2_s()), ("P4", P4.s)):
    for rho in (0.059, 0.0992, 0.1394, 0.26):
        prof = Profile("%s|%g" % (sn, rho), s, rho, P4.rho_lu, "")
        for tm in (5, 8):
            for d in ("code", "chat", "edit"):
                reqs = [r for r in R if r["domain"] == d]
                a = T.trace(GateV2(tmax=tm), reqs, prof); b = T.trace(GateV2Native(tmax=tm), reqs, prof)
                first = next((k for k, (x, y) in enumerate(zip(a, b)) if x != y), None)
                ok = len(a) == len(b) and first is None; bad += not ok
                if not ok: print("tf_d7 DIFF", sn, rho, tm, d, first, a[first] if first is not None else None, b[first] if first is not None else None)
print("TF_D7+SYNTH", "PASS" if bad == 0 else "FAIL %d" % bad)
