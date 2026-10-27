# strataplus-H1-arbiter-v1.patch

- sha256: `9e54345ccb9159921971cd3bcd845ba79cdd212ee91b15459e4bc344f1c323e6`
- Base: `b24c6a1d` (melchisedekko/Strata main). Cumulative diff = P1-P6 rebased onto b24c6a1d (no conflicts) + H1 v1.
  Local commit `e959072a` on `strataplus-h1-hlang-local` (worktree /workspace/policy-local/h1_worktree). Not pushed.
- Apply: `git apply strataplus-H1-arbiter-v1.patch` at the repo root -> `git apply --check` rc=0 on b24c6a1d.
- 21 files, +1643/-10. No data, no secrets, no files named after the non-publishable-license edit dataset.

## What it adds (OFF by default = upstream)
- `STRATA_SPEC_JOINT=1`: JointGate arbiter (P5/P6, already announced).
- `STRATA_SPEC_JOINT_DET=1` (needs JOINT=1): deterministic arbiter. Frozen cost table, and the feedback is the table's
  `cost_pred(t,d,k)`, not the measured ms. DraftPolicy costs are frozen too. Does not depend on round_ms. Only chooses
  what gets verified, never which tokens are emitted.
- `STRATA_SPEC_JOINT_COST="s1,..,s8;rho_mtp;rho_lu"` (optional). Unset = gate priors.
- Validated before the model load. DET not 0/1, or COST malformed -> exit 1. DET without JOINT / COST without DET -> warning.
- SYCL: "warning: <VAR> ignorata su SYCL". qwen35moe: warning, not patched.
- Docs: docs/strataplus_joint_det.md. Tests: ctest joint_det_test, strataplus/tests/run_policy_checks.sh,
  strataplus/tests/greedy_identity.py (prepared, NOT run: it loads a model).

## Checks (box, nice 19, -j<=2, logged in /workspace/strata-plus/cpu_busy_policy.log; times CET 26/10/2026)
- Host build strata_spec + 7 tests: rc=0, 0 warnings. 7/7 PASS (22:16).
- Syntax check src/program/generate.cpp HIP + CUDA: rc=0. Warnings identical to the b24c6a1d control (132 HIP / 1 CUDA, path only) (22:16).
- Flag-off DraftPolicy identity vs b24c6a1d, 20000 rounds x 8 configs: 160008 lines, sha256 e36b6a30... on both sides.
- Det mode: same sha256 across 2 runs and 3 timing profiles (priors bf4f163b...; table e026ee02...). Negative
  control (live timing) differs, as expected (22:16).
- HIP gfx1100 TUs (generate.cpp.o + strata_spec), final tree vs control: rc 0/0, 131 = 131 warnings, same set.
- NOT done: full `strata` link (80 HIP objects, did not fit before the a' window). Deferred:
  /workspace/policy-local/hip_build_deferred.sh. gfx1201: impossible on the box (ROCm/HIP 5.7.31921, clang 17.0.6:
  "invalid target ID 'gfx1201'").
