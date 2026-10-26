"""ctypes binding to the PRODUCTION strata_spec code (native/libstrata_spec_capi.so, built from
/workspace/strata-src @ 7dd5cf18 + native/strata_spec_capi.cpp). NativeDraftPolicy exposes the same methods the
replay uses on the Python port (draft_policy_port.DraftPolicy), so either backend can drive policies.Current.
Set STRATA_SPEC_LIB to load another build (e.g. the patched library of patches/draft_policy_v2.diff)."""
from __future__ import annotations
import ctypes as C, os
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT = os.path.join(_HERE, "..", "native", "libstrata_spec_capi.so")
_libs = {}


def lib(path=None):
    path = os.path.abspath(path or os.environ.get("STRATA_SPEC_LIB", _DEFAULT))
    if path in _libs:
        return _libs[path]
    L = C.CDLL(path)
    vp, i, d, ll, ull = C.c_void_p, C.c_int, C.c_double, C.c_longlong, C.c_ulonglong
    fp, dp, ip, i32p = C.POINTER(C.c_float), C.POINTER(C.c_double), C.POINTER(C.c_int), C.POINTER(C.c_int32)
    sig = {
        "dp_new": (vp, [i, d]), "dp_free": (None, [vp]), "dp_set_robust": (None, [vp, i]),
        "dp_set_context": (None, [vp, ll]), "dp_seed_costs": (None, [vp, dp, i, d, i]),
        "dp_choose": (i, [vp, i, i, i]), "dp_observe": (None, [vp, i, i, i, i, d]),
        "dp_observe_probs": (None, [vp, fp, i, i]), "dp_lookup_rate": (d, [vp, i]), "dp_cost_ms": (d, [vp, i]),
        "dp_chain_rows": (i, [vp, fp, i, ip]),
        "sd_new": (vp, [i, i, ull]), "sd_free": (None, [vp]), "sd_reset": (None, [vp]),
        "sd_append": (None, [vp, i32p, ull]), "sd_propose": (i, [vp, i, i32p]), "sd_last_match": (i, [vp]),
        "sd_size": (ull, [vp]), "sd_scan": (None, [vp, i32p, i, i, ip, ip, ip, i32p]),
    }
    for name, (res, args) in sig.items():
        f = getattr(L, name)
        f.restype, f.argtypes = res, args
    # optional entry points of the patched library
    for name, args in (("dp_observe_counterfactual", [vp, i, i, i, i, i, i]), ("dp_set_frozen_costs", [vp, i])):
        if hasattr(L, name):
            f = getattr(L, name)
            f.restype, f.argtypes = None, args
    _libs[path] = L
    return L


class NativeDraftPolicy:
    def __init__(self, max_t, margin=0.03, libpath=None):
        self.L = lib(libpath)
        self.h = self.L.dp_new(max_t, margin)
        self._robust = False

    def __del__(self):
        try:
            self.L.dp_free(self.h)
        except Exception:
            pass

    @property
    def robust(self):
        return self._robust

    @robust.setter
    def robust(self, v):
        self._robust = bool(v)
        self.L.dp_set_robust(self.h, int(bool(v)))

    def set_context(self, pos):
        self.L.dp_set_context(self.h, int(pos))

    def seed_costs(self, ms, n, weight, bucket=0):
        arr = (C.c_double * n)(*ms[:n])
        self.L.dp_seed_costs(self.h, arr, n, weight, bucket)

    def choose(self, t_mtp, lookup_k, match):
        r = self.L.dp_choose(self.h, t_mtp, lookup_k, match)
        return (r < 0), abs(r)

    def observe(self, lookup, t, accepted, match, round_ms):
        self.L.dp_observe(self.h, int(lookup), t, accepted, match, round_ms)

    def observe_probs(self, p, n, accepted):
        arr = (C.c_float * max(n, 1))(*[float(x) for x in p[:n]])
        self.L.dp_observe_probs(self.h, arr, n, accepted)

    def lookup_rate(self, match):
        return self.L.dp_lookup_rate(self.h, match)

    def cost_ms(self, t):
        return self.L.dp_cost_ms(self.h, t)

    def mtp_chain_rows(self, probs, cap):
        arr = (C.c_float * 8)(*[float(x) for x in list(probs[:8]) + [0.0] * (8 - len(probs[:8]))])
        st = C.c_int(0)
        rows = self.L.dp_chain_rows(self.h, arr, cap, C.byref(st))
        return rows, st.value

    # patched library only (patches/P2_deterministic_cost.diff + P3_counterfactual_feedback.diff)
    def observe_counterfactual(self, lookup, t, accepted, failure_seen, match, n_mtp=0):
        self.L.dp_observe_counterfactual(self.h, int(lookup), t, accepted, int(failure_seen), match, n_mtp)

    def set_frozen_costs(self, on):
        self.L.dp_set_frozen_costs(self.h, int(bool(on)))


class NativeSuffixDrafter:
    def __init__(self, min_match=3, max_match=64, capacity=1 << 22, libpath=None):
        self.L = lib(libpath)
        self.h = self.L.sd_new(min_match, max_match, capacity)

    def __del__(self):
        try:
            self.L.sd_free(self.h)
        except Exception:
            pass

    def reset(self):
        self.L.sd_reset(self.h)

    def append(self, toks):
        a = np.ascontiguousarray(np.asarray(toks, dtype=np.int32))
        self.L.sd_append(self.h, a.ctypes.data_as(C.POINTER(C.c_int32)), len(a))

    def size(self):
        return self.L.sd_size(self.h)

    def scan(self, y, max_k, want_tokens=True):
        """Teacher-forced pass over y (appends y): per position i the proposal made with history (...+y[:i]),
        its match length and acceptance LCP(proposal, y[i:]). Production SuffixDrafter::propose()."""
        y = np.ascontiguousarray(np.asarray(y, dtype=np.int32))
        n = len(y)
        k = np.zeros(n, np.int32); m = np.zeros(n, np.int32); acc = np.zeros(n, np.int32)
        tok = np.full((n, max_k), -1, np.int32) if want_tokens else None
        ip = C.POINTER(C.c_int)
        self.L.sd_scan(self.h, y.ctypes.data_as(C.POINTER(C.c_int32)), n, max_k, k.ctypes.data_as(ip),
                       m.ctypes.data_as(ip), acc.ctypes.data_as(ip),
                       tok.ctypes.data_as(C.POINTER(C.c_int32)) if want_tokens else None)
        return k, m, acc, tok
