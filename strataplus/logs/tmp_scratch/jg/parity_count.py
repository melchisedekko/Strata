import sys
sys.path.insert(0, "/workspace/strata-policy/replay"); sys.path.insert(0, "/workspace/strata-policy/replay/tests")
import strata_sim.sim2 as S
S.P3_LIB = sys.argv[1]
import test_joint_gate_parity as T
from strata_sim.synth2 import make_domain
from strata_sim.postprocess import load_tf
from strata_sim.sim2 import GateV2, GateV2Native, base_profiles, load_p4, S_P1, p2_s, Profile
def cmp(kw, reqs, prof):
    a = T.trace(GateV2(**kw), reqs, prof); b = T.trace(GateV2Native(**kw), reqs, prof)
    div = sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b)); return len(a), div
nc = nr = nd = 0
for dom in ("code", "chat", "edit", "session"):
    reqs = make_domain(dom, 6, 3)
    for prof in base_profiles()[:3]:
        for kw in ({}, {"conf_stop": True}, {"skip": False}, {"srcs": ("lk", "pl")}, {"srcs": ()}):
            r, d = cmp(kw, reqs, prof); nc += 1; nr += r; nd += d
print("SYNTH configs", nc, "rounds", nr, "divergent", nd)
R = load_tf("/workspace/strata-plus/traces/tf_d7.jsonl"); P4 = load_p4(sys.argv[2]); print("P4 s", P4.s); tc = tr = td = 0
for sn, s in (("P1", S_P1), ("P2", p2_s()), ("P4", P4.s)):
    for rho in (0.059, 0.0992, 0.1394, 0.26):
        prof = Profile("x", s, rho, P4.rho_lu, "")
        for tm in (5, 8):
            for d in ("code", "chat", "edit"):
                r, dv = cmp({"tmax": tm}, [q for q in R if q["domain"] == d], prof); tc += 1; tr += r; td += dv
print("TF_D7 configs", tc, "rounds", tr, "divergent", td)
