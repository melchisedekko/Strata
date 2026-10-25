# Strata+ P5 — joint source+depth gate: engine wiring (DESIGN, not compiled)


## Final local configuration (Strata Lead decision, 25/10/2026): arm A

`STRATA_SPEC_JOINT=1` selects JointGate with `JointGate::Options()` as is = **arm A**: tmax=5 (windows T<=5, d<=4),
skip=true (lookup-first), prompt lookup only, no conf_stop, no hazard decay (frozen_params_v3.json, sha256 37bf1996...).
`JointGate::enabled_from_env()` reads the variable; without it nothing changes (DraftPolicy, upstream 7dd5cf18).
C++ defaults == replay GateV2(tmax=5, skip=True) round by round (replay/tests/test_arm_a_default_parity.py: tune
tf_d7 x P1/P2/P4 x rho band + 0.26 x cost V1/V2, and the synthetic domains; nothing tuned on the holdout).

**LIMITS**
- Single sequence only (CLI and the --serve GEN loop). batch_step / BGEN does not use DraftPolicy: no effect for parallel > 1.
- tok/s are ESTIMATED by the replay on a CPU proxy (Qwen3.5-2B Q4_K_M), not AMD measurements.
- Holdout v1.1: vs the default a gain in all three domains in the rho band 0.06-0.15; vs k=3 no cell clearly worse.
- Vs STRATA_SPEC_COST=1, chat: no gain and one cell clearly worse (chat, P1, rho 0.0791: -1.4% [-2.8; -0.2]). This agrees
  with the H4(a) NO-GO; P1 is a cost profile estimated from the code, not measured.
- Holdout v1.1 is used: any future comparison needs a new holdout.
- The engine wiring below (generate.cpp) is still a DESIGN: not written/compiled here (CUDA headers).

**Scope (Strata Lead decision): single sequence only.**  JointGate / gate_v2 replaces DraftPolicy where DraftPolicy
runs: the CLI generation loop and the GEN loop of `--serve` (one request served alone).  The batch path
(`batch_step`, `BGEN <slot>`, generate.cpp ~11519 at 7dd5cf18) does not call DraftPolicy: each slot verifies 2 rows
(the token + ONE MTP draft from its `slot_mtp`, `draft(2, ...)`).  So this patch changes nothing for batched serving and
any gain measured for gate_v2 holds for requests served alone, NOT for a server with parallel > 1.  Extending the
batch path (more than 2 rows per slot, a per-slot pool) is follow-up H2b (after gate_v2, needs a GPU); a persistent
pool for requests served alone is H2a (paused until session traces exist).

`strata::spec::JointGate` (include/strata/spec/joint_gate.hpp) is compiled and unit-tested
(src/spec/joint_gate_test.cpp) and is decision-for-decision identical to the replay's GateV2
(replay/tests/test_joint_gate_parity.py: 60 configurations, every round identical).  Its wiring into the serve loop
(src/program/generate.cpp) is NOT part of this patch: generate.cpp needs CUDA headers to compile and could not be
built here.  Proposed wiring, behind `STRATA_SPEC_JOINT=1` (DraftPolicy stays the default):

1. Next-round drafting happens at the end of a round (`mtp.draft(...)`, generate.cpp ~15193 at 7dd5cf18).  Before it,
   the lookup proposal for the next round is already computable (sfx has the committed tokens): call
   `sfx.propose` / `propose_from_sources` (pool, P4) there, and `gate.start(lu, JointGate::remaining(max_new, produced_n, o.max_context, p), &c)` (bounded by the context window too: the engine stops at `p + T > max_context`).
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
