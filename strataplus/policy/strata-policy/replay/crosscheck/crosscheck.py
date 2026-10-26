"""Random op streams through the compiled C++ DraftPolicy and the Python port; any divergence fails."""
import random, subprocess, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from strata_sim.draft_policy_port import DraftPolicy

def stream(seed, n=4000):
    r = random.Random(seed); ops = []; robust = seed % 2
    ops.append(("R", robust)); pos = 0
    for _ in range(n):
        pos += r.randint(1, 400)
        if r.random() < 0.3: ops.append(("X", pos % 40000))
        x = r.random()
        if x < 0.4: ops.append(("C", r.randint(1, 6), r.choice([0, 0, 1, 2, 3, 5, 7]), r.randint(3, 40)))
        elif x < 0.75: ops.append(("O", r.randint(0, 1), r.randint(1, 8), r.randint(0, 7), r.randint(3, 40), round(r.uniform(-1, 80), 3)))
        elif x < 0.88:
            k = r.randint(1, 5); ops.append(("P", k, [round(r.random(), 4) for _ in range(k)], r.randint(0, k)))
        else:
            cap = r.randint(2, 6); ops.append(("K", cap, cap - 1, [round(r.random(), 4) for _ in range(cap - 1)]))
    return ops

def to_text(ops):
    out = []
    for o in ops:
        if o[0] == "P": out.append(f"P {o[1]} {' '.join(map(str, o[2]))} {o[3]}")
        elif o[0] == "K": out.append(f"K {o[1]} {o[2]} {' '.join(map(str, o[3]))}")
        else: out.append(" ".join(map(str, o)))
    return "\n".join(out) + "\n"

def py_run(ops):
    import numpy as np
    pol = DraftPolicy(6); res = []
    for o in ops:
        if o[0] == "R": pol.robust = bool(o[1])
        elif o[0] == "X": pol.set_context(o[1])
        elif o[0] == "C": l, t = pol.choose(o[1], o[2], o[3]); res.append(f"C {int(l)} {t}")
        elif o[0] == "O": pol.observe(bool(o[1]), o[2], o[3], o[4], o[5])
        elif o[0] == "P": pol.observe_probs([float(np.float32(v)) for v in o[2]], o[1], o[3])
        elif o[0] == "K":
            rows, steps = pol.mtp_chain_rows([float(np.float32(v)) for v in o[3]], o[1]); res.append(f"K {rows} {steps}")
    return res

if __name__ == "__main__":
    exe = sys.argv[1]; bad = 0; total = 0
    for seed in range(40):
        ops = stream(seed)
        cpp = subprocess.run([exe], input=to_text(ops), capture_output=True, text=True).stdout.split("\n")[:-1]
        py = py_run(ops); total += len(py)
        if cpp != py:
            bad += 1
            i = next(i for i, (a, b) in enumerate(zip(cpp, py)) if a != b) if len(cpp) == len(py) else -1
            print(f"seed {seed}: MISMATCH at answer {i}: cpp={cpp[i] if i>=0 else len(cpp)} py={py[i] if i>=0 else len(py)}")
    print(f"crosscheck: {total} answers compared, {bad} mismatching streams")
    sys.exit(1 if bad else 0)
