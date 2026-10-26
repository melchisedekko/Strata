import sys, runpy
sys.path.insert(0, "/workspace/strata-policy/replay")
import strata_sim.sim2 as S
orig = S.load_p4
def lp(*a, **k):
    p = orig(*a, **k); p.s[7] = p.s[6] + (p.s[6] - p.s[5]); return p   # s(8) linear from s(6), s(7)
S.load_p4 = lp
sys.argv = ["verify_ab.py", "results/v2/verify_ab/new_s8lin.json"]
runpy.run_path("verify_ab.py", run_name="__main__")
