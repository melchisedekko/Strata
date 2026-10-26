"""Parity: the C++ JointGate (patch P5) takes the same decisions as the replay's GateV2 (Python control)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from strata_sim.synth2 import make_domain
from strata_sim.sim2 import GateV2, GateV2Native, base_profiles, walk


def trace(pol, reqs, prof):
    acts = []
    orig = pol.act
    def act(q, i, pr):
        r = orig(q, i, pr); acts.append((r[0], int(r[1]), int(r[2]), int(r[3]))); return r
    pol.act = act
    walk(pol, reqs, prof)
    return acts


def main():
    bad = 0
    for dom in ("code", "chat", "edit", "session"):
        reqs = make_domain(dom, 6, 3)
        for prof in base_profiles()[:3]:
            for kw in ({}, {"conf_stop": True}, {"skip": False}, {"srcs": ("lk", "pl")}, {"srcs": ()}):
                a = trace(GateV2(**kw), reqs, prof)
                b = trace(GateV2Native(**kw), reqs, prof)
                same = sum(x == y for x, y in zip(a, b))
                first = next((k for k, (x, y) in enumerate(zip(a, b)) if x != y), None)
                ok = len(a) == len(b) and first is None
                bad += not ok
                print(f"{dom:8s} {prof.name:7s} {str(kw):28s} rounds {len(a):5d}/{len(b):5d} same {same:5d} "
                      f"{'ok' if ok else 'DIFF at ' + str(first) + ' ' + str(a[first]) + ' vs ' + str(b[first])}")
    print("PASS" if bad == 0 else f"FAIL ({bad})")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
