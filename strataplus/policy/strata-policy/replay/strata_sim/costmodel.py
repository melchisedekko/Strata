"""Symbolic round-cost model (SYNTHETIC unless its parameters are fitted from real logs).

T_round(src, k, kd) = c_verify(k) + c_mtp(kd) + c_lookup
  c_verify(k) = a + b*k        k = drafts in the verified window (window rows T = k+1); k = 0 is "no speculation"
  c_mtp(kd)   = m*kd           kd = MTP drafts actually computed this round
  c_lookup    = c              suffix index probe (always paid when lookup is enabled)
Modes for kd:
  always    - as Strata today: the MTP chain is drafted after every commit, before choose() (generate.cpp:15168),
              so a lookup/none round still pays the drafts the policy planned (kd = planned MTP depth)
  on_demand - idealised "no double work": a lookup/none round pays only the first MTP draft (needed for the
              agreement gate sbuf[0]==drafts[0], generate.cpp:14899); an MTP round pays its kd drafts
Per-round multiplicative noise (lognormal sigma, plus rare spikes) is shared by all policies (common random numbers).
"""
from __future__ import annotations
import random, math
from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    a: float = 20.0      # ms, one-row verify (the unit; everything else is a fraction of it in the sweeps)
    b: float = 7.0       # ms per extra window row
    m: float = 0.6       # ms per MTP draft
    c: float = 0.06      # ms lookup probe
    mode: str = "always"
    sigma: float = 0.08
    spike_p: float = 0.02

    def kd_paid(self, src: str, kd: int) -> int:
        if self.mode == "always" or src == "mtp":
            return kd
        return min(kd, 1)

    def mean(self, src: str, k: int, kd: int) -> float:
        return self.a + self.b * k + self.m * self.kd_paid(src, kd) + self.c

    def label(self) -> str:
        return f"b/a={self.b/self.a:.2f} m/a={self.m/self.a:.3f} c/a={self.c/self.a:.4f} {self.mode}"


def noise_vector(n: int, seed, sigma=0.08, spike_p=0.02):
    r = random.Random(f"noise-{seed}")
    out = []
    for _ in range(n):
        x = math.exp(r.gauss(0.0, sigma) - sigma * sigma / 2)
        if r.random() < spike_p:
            x *= r.uniform(1.5, 3.0)
        out.append(x)
    return out
