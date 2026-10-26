"""Parity for the FINAL local patch: the C++ JointGate built with its DEFAULTS (JointGate(), i.e. what STRATA_SPEC_JOINT=1
gets: arm A) takes, round by round, the same decision (src, T, d, k_lu) as the replay's arm A, GateV2(tmax=5, skip=True).
Data: tune tf_d7 (traces/tf_d7.jsonl, P1/P2/P4 x rho band + 0.26, cost V1 and V2) and the synthetic domains.
No holdout data is read.  Library: native/libstrata_spec_capi_p5a.so (built from the final commit)."""
import sys, os, ctypes as C
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
from strata_sim.sim2 import GateV2, GateV2Native, Profile, load_p4, S_P1, p2_s, base_profiles, walk
from strata_sim.synth2 import make_domain
from strata_sim.postprocess import load_tf
from strata_sim.native import lib

LIB = os.path.join(HERE, "..", "native", "libstrata_spec_capi_p5a.so")
TUNE = "/workspace/strata-plus/traces/tf_d7.jsonl"
COST = {"V1": "/workspace/strata-plus/traces/cost_p4_cpu.json",
        "V2": os.path.join(HERE, "..", "cost_derived", "cost_p4_cpu_099ceda_s8lin.json")}


class DefaultNative(GateV2Native):
    """GateV2Native whose handle is JointGate() (defaults), not jg_new(...) with replay parameters."""
    def __init__(self):
        self.L = L = lib(LIB)
        ip, fp = C.POINTER(C.c_int), C.POINTER(C.c_float)
        L.jg_new_default.restype = C.c_void_p; L.jg_new_default.argtypes = []
        L.jg_free.argtypes = [C.c_void_p]
        L.jg_act.argtypes = [C.c_void_p, C.c_int, ip, fp, fp, ip]
        L.jg_observe.argtypes = [C.c_void_p, ip, C.c_int, C.c_double, C.c_int, fp, ip, ip]
        self.C = C
        self.h = L.jg_new_default()
        self.srcs = ("lk",)
        self.name = "jointgate_default_native"


def trace(pol, reqs, prof):
    acts = []; orig = pol.act
    def act(q, i, pr):
        r = orig(q, i, pr); acts.append((r[0], int(r[1]), int(r[2]), int(r[3]))); return r
    pol.act = act; walk(pol, reqs, prof)
    return acts


def cmp(tag, reqs, prof, tot):
    a = trace(GateV2(tmax=5, skip=True), reqs, prof); b = trace(DefaultNative(), reqs, prof)
    first = next((k for k, (x, y) in enumerate(zip(a, b)) if x != y), None)
    ok = len(a) == len(b) and first is None
    tot["cfg"] += 1; tot["rounds"] += len(a); tot["bad"] += not ok; tot["maxT"] = max(tot["maxT"], max(x[1] for x in b))
    if not ok:
        print(f"{tag:34s} rounds {len(a)}/{len(b)} DIFF at {first}: {a[first] if first is not None else ''} vs {b[first] if first is not None else ''}")


def main():
    L = lib(LIB); L.jg_default_tmax.restype = C.c_int
    print("JointGate() tmax =", L.jg_default_tmax())
    tot = dict(cfg=0, rounds=0, bad=0, maxT=0)
    R = load_tf(TUNE)
    for V, cp in COST.items():
        P4 = load_p4(cp)
        for sn, s in {"P1": S_P1, "P2": p2_s(), "P4": P4.s}.items():
            for r in (0.059, 0.0791, 0.0992, 0.1193, 0.1394, 0.26):
                prof = Profile("%s|rho%.4f" % (sn, r), s, r, P4.rho_lu, "band" if r < 0.2 else "ctrl")
                for dom in ("code", "chat", "edit"):
                    cmp(f"tune {V} {dom} {prof.name}", [q for q in R if q["domain"] == dom], prof, tot)
    t1 = dict(tot); print("tune tf_d7:", t1)
    for dom in ("code", "chat", "edit", "session"):
        reqs = make_domain(dom, 6, 3)
        for prof in base_profiles():
            cmp(f"synth {dom} {prof.name}", reqs, prof, tot)
    print("tune+synth:", tot, "synth only cfg", tot["cfg"] - t1["cfg"], "rounds", tot["rounds"] - t1["rounds"])
    print("PASS" if tot["bad"] == 0 and L.jg_default_tmax() == 5 else "FAIL")
    return tot["bad"]


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
