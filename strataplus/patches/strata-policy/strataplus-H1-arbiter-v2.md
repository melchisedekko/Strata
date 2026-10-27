# strataplus-H1-arbiter-v2.patch

- sha256: `e7b9b48cfe7f60388af076469e721b145957168005c5caea51b40edb0a1ba623` (v1 files unchanged).
- Base: `b24c6a1d`. Cumulative diff = P1-P6 rebased + H1 v1 (`e959072a`) + H1 v2 (`719b4d66`), branch
  `strataplus-h1-hlang-v2-local` in /workspace/policy-local/h1_worktree. Local only, not pushed.
- Apply: `git apply strataplus-H1-arbiter-v2.patch` on b24c6a1d (`git apply --check` rc=0). 21 files, +1689/-10.
- No data, no secrets, no files named after the non-publishable-license edit dataset.

## New in v2
- `STRATA_SPEC_COST_FROZEN` and `STRATA_SPEC_JOINT_DET` are mutually exclusive. "Set" means non-null, non-empty and not "0".
  - With both set, startup exits with rc=1 BEFORE the model load. Message: `strata: STRATA_SPEC_COST_FROZEN=.. and STRATA_SPEC_JOINT_DET=.. are mutually exclusive (Strata+ H-FC vs H1 deterministic arbiter): unset one of them`.
  - Only the env is checked; H-FC is not in the tree.
  - Code: `include/strata/spec/joint_det.hpp` L30/L32 and `src/spec/joint_det.cpp` L10-16 (`joint_det_frozen_conflict[_env]`). It is the first check in `plus_h1_validate()` (generate.cpp L1221-1226 on 719b4d66; L1227-1232 on the final tree).
  - `plus_h1_validate()` is called once after arg parsing, for both CLI and serve, at L2954 (719b4d66) / L2966 (final).
  - Host test: `joint_det_test`, 3 new checks.
- Docs: "## v2" section in docs/strataplus_joint_det.md, with the model path.

## Model path (Qwen3.8-Flash-Next = arch `qwen4exp` -> main generate.cpp path, NOT qwen35::run)
- `include/strata/artifact/model_family.hpp` on b24c6a1d (file not touched):
  - L22 `if (arch == "qwen4exp")`, and L23 qwen35moe;
  - L51: the comment on which engine path each family takes.
- generate.cpp dispatch:
  - b24c6a1d: L2404 `bool qwen35 = false;`, L2411 `strata::qwen35::run`;
  - 719b4d66: L2552/L2563;
  - final: L2558/L2574.
  - qwen4exp does not enter that branch, so it passes through `plus_h1_validate` (validation and the rc=1 conflict check).
- Two DraftPolicy instances:

  | Site | b24c6a1d | 719b4d66 | final |
  |---|---|---|---|
  | serve `DraftPolicy policy(S)` | L11214 | L11369 | L11396 |
  | serve JointHook (`make_joint_hook`) | n/a | L11373 | L11400 |
  | serve frozen costs | n/a | L11381 | L11414 |
  | CLI `DraftPolicy policy(o.spec)` | L16492 | L16753 | L16800 |
  | CLI JointHook | n/a | L16757 | L16804 |
  | CLI frozen costs | n/a | L16779 | L16826 |

  `make_joint_hook` is defined at L1196 (719b4d66) / L1202 (final).
- What the hook does:

  | Path | Lines | Behaviour |
  |---|---|---|
  | Serve, serial GEN loop | `joint->decide` L15129 (719b4d66) / L15176 (final); `policy.choose` b24 L14936 -> L15146/L15193; `joint->observe` L15475/L15522 | JointHook picks T and the source. In DET mode the feedback is `cost_pred`, not ms |
  | CLI, serial | `joint->decide` L16898/L16945; `policy.choose` b24 L16623 -> L16904/L16951; `joint->observe` L17058/L17105 | Same as serve serial |
  | Serve, pipeline T (`--spec-pipeline`) | `policy.choose(w.T, …)` b24 L14507 -> L14682/L14727 | Gets only DraftPolicy with frozen costs (DET => frozen). The JointHook is NOT called there |
- NOT covered:
  - the JointHook in pipeline windows;
  - `--batch`/BGEN (no DraftPolicy there);
  - qwen35/qwen35moe (warning only).
- Serve per-round trace: absent. `STRATA_SPEC_TRACE` is CLI only (b24 L16468; final L16775). A trace recording the path (serial/pipeline) when DET is on would go next to `joint->decide` (serial, L15176) and at `w.T = pk.t` (pipeline, final L14729). It is documented here, not implemented.

## Checks (26/10/2026, CET; nice 19, -j<=2, logged in /workspace/strata-plus/cpu_busy_policy.log)
- Host build strata_spec + joint_det_test on 719b4d66: rc=0, 0 warnings, all ok (22:28).
- The final tree (H1 v2 + LANG v2) was checked as follows:
  - Host build strata_spec + 8 tests: rc=0, 0 warnings, 8/8 rc=0 (22:30).
  - Syntax check HIP/CUDA: rc=0/0, warnings identical to the control (132 HIP) (22:30).
  - HIP gfx1100 TU-only (generate.cpp.o + strata_spec) with Debian HIP 5.7: rc=0, 131 = 131 control warnings, same multiset (22:30:17-22:31:12).
  - run_policy_checks.sh N=20000 (22:31):
    - flag-off identity vs b24c6a1d: 160008 lines, sha256 e36b6a30… on both sides;
    - det reproducible: priors bf4f163b…, table e026ee02…, the same across 2 runs and 3 profiles;
    - the live negative control differs, as expected.
- `git apply --check`: this patch on b24c6a1d rc=0; LANG v2 on top rc=0. Tree = 560464ef (35503e9b).
- NOT done:
  - full link with HIP 5.7 (it fails on the control too);
  - gfx1201 with HIP 5.7.
  - Prepared but not run:
    - `/workspace/policy-local/hip_build_deferred_v2.sh` (TU-only gfx1100, v2 vs control);
    - `/workspace/policy-local/hip_build_full_rocm644.sh --bench-window-ended` (ROCm 6.4.4, gfx1100;gfx1201, full link ctrl / H1 v2 / H1 v2+LANG v2).
