# Strata+ P5 — joint source+depth gate: engine wiring (DESIGN, not compiled)

`strata::spec::JointGate` (include/strata/spec/joint_gate.hpp) is compiled and unit-tested
(src/spec/joint_gate_test.cpp) and is decision-for-decision identical to the replay's GateV2
(replay/tests/test_joint_gate_parity.py: 60 configurations, every round identical).  Its wiring into the serve loop
(src/program/generate.cpp) is NOT part of this patch: generate.cpp needs CUDA headers to compile and could not be
built here.  Proposed wiring, behind `STRATA_SPEC_JOINT=1` (DraftPolicy stays the default):

1. Next-round drafting happens at the end of a round (`mtp.draft(...)`, generate.cpp ~15193 at 7dd5cf18).  Before it,
   the lookup proposal for the next round is already computable (sfx has the committed tokens): call
   `sfx.propose` / `propose_from_sources` (pool, P4) there, and `gate.start(lu, max_new - produced_n - 1, &c)`.
   - `start()` true: skip `mtp.draft` (d = 0); the next round verifies the lookup window `c.t` (or T = 1).
   - false: draft with `mtp.set_chain_rule([&](int idx, float pj) { probs[idx] = pj; return gate.keep(probs, ent, idx + 1); })`
     (the same hook `keep_draft` uses for STRATA_SPEC_COST; `ent` = the optional per-draft entropy of log_format D11,
     null if the MTP head does not expose it - then conf_stop falls back to -log p).
2. Round start: `c = gate.finish(probs, d, lu)` with `lu[s].agree = (sbuf[0] == drafts[0])`.  This replaces both
   `policy.choose` and the agreement gate (the gate learns P(accept | agree) instead of requiring agreement).
3. After the commit: `gate.observe(c, a, round_ms, mtp_acc, probs, lu, lu_acc)` with the a+1-censored LCPs of the
   MTP drafts and of each lookup proposal against `outv[0..a]` (P1's `plus_lcp`, computed before `mtp.draft`
   overwrites `drafts`).  The cost is the round's measured ms (or, with STRATA_SPEC_COST_FROZEN=1, the seeded table:
   `set_frozen(true)` after a first observe sets the scale).
4. Chained windows (--lookup-chain) are out of scope of the gate: keep them on DraftPolicy::chain.

Risks to measure live (the replay cannot): the draft time of the MTP head at depth > S_mtp - 1 (engine cap), the
cost of a skipped draft when the lookup then fails (the MTP must draft at the start of the next round, serialised),
and the warm-up of the RLS cost model (optimistic prior: it tries deep windows early).
