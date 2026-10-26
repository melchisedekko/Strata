# strataplus-LANG-knob-v2.patch

- sha256: `18122e6bd7696905d645c283c45cfb7c6e616b74ea43c1ec0f9f3f3d9287e2a8` (v1 files unchanged).
- Base: b24c6a1d + `strataplus-H1-arbiter-v2.patch` (= `719b4d66`). Commits `6b7dea81` (LANG v1) and `560464ef` (LANG v2). Local only, not pushed.
- Apply: `git apply strataplus-LANG-knob-v2.patch` after H1 v2 (`git apply --check` rc=0; the resulting tree equals 560464ef).
- 11 files, +710/-4. No data, no secrets, no files named edit_np.

## New in v2
1. **Pipeline T** (serve `--spec-pipeline`).
   - v1 applied only the language's `spec_min_p` (via `req_spec_min_p`, set by `resolve_lang`).
   - v2 adds `lang_window(lang_c, T, S_mtp, pr+from, avail-from)` in the `t_rule` lambda when the language matched and its rule is not default.
   - It runs before the clamp `max(1, min(T, 1+avail-from))`. T is never above the chain outputs, S_mtp or 8.
2. **Example table.**
   - Renamed to `strataplus/tests/lang_table_EXAMPLE_not_calibrated.json`, with `"example_not_calibrated": true` and comment "ESEMPIO, non calibrata".
   - No default path: it is loaded only via `--spec-lang-table` / `STRATA_SPEC_LANG_TABLE`.
   - The loader marks a table as an example via the bool field, or a top-level comment/_comment/source containing "ESEMPIO" (`src/spec/lang_knob.cpp` L180-193, L244; `lang_knob.hpp` L45-52).
   - serve then prints `strata: WARNING: <path> is an EXAMPLE language table (ESEMPIO, non calibrata) ...` (generate.cpp L2979).
3. **serve/server.py.**
   - `STRATA_LANG_RE` at L90.
   - `StrataEngine.sampling_keys` (L1391) at L1445-1450 forwards the request field `"strata_lang"` as the GEN key ` strata_lang=<name>`, only for a plain name (`[A-Za-z0-9_+#.-]{1,32}`).
   - The HTTP body already reaches `sampling` whole. frontend.py filters nothing, so the end-to-end test passes.
   - BGEN/GEN use the same keys.
   - Field absent: the GEN line is byte-identical.
   - Engine without a table: the key is skipped like any unknown key, so behaviour is identical.
   - Test: `serve/test_strata_lang.py` (stand-in engine, no model), 4/4 OK. The existing `serve.test_server.SamplingKeys` 6/6 still pass.

## Model path (qwen4exp -> main generate.cpp path)
- The table is loaded and validated before the model load, at final L2966-2979, after `plus_h1_validate`.
- qwen35 branch: final L2571-2574, where `--spec-lang-table` gets a warning that it is ignored on qwen35moe.
- On b24c6a1d none of these exist; the dispatch is at L2411.
- Serve, per request:

  | Step | b24c6a1d | final |
  |---|---|---|
  | GEN key parse | `spec_min_p` L12387 | `spec_min_p` L12586; `strata_lang` L12587 |
  | BGEN rewrite to "GEN 1" (same parser) | L12050 | L12247 |
  | `resolve_lang` | n/a | L12608 |
  | `req_draft_min_p = lang_c.draft_min_p` | n/a | L12610 |
  | serial GEN loop, `lang_window` | `policy.choose` L14936 | `lang_window` L15146; `policy.choose` L15193 |
  | serial drafter `mtp.draft(…, req_draft_min_p)` | `req_spec_min_p` L15208 | L15465 |
  | pipeline `t_rule` | L14391 | L14607, with `lang_window` at L14616 |
  | pipeline `policy.choose(w.T, …)` | L14507 | L14727 |

  In the serial loop the language's T rule runs before the JointHook (L15176) and before DraftPolicy (L15193).
- NOT covered:
  - **CLI** (`strata generate` has no request; its drafter uses `o.spec_min_p`): DraftPolicy b24 L16492 -> final L16800; `mtp.draft` b24 L16592 -> final L16909. This is by design.
  - `--batch`/BGEN slots: the key is parsed, but the batched path has no T rule or DraftPolicy.
  - qwen35/qwen35moe.
  - In the pipeline, a `fixed` rule can be cut short by the chain, which is drafted with the pipeline's floor rather than floor 0 as in the serial loop.
  - S / S_mtp / lookup cap are never changed.
- Per-round serve trace: absent (STRATA_SPEC_TRACE is CLI only, final L16775). A path tag would go at the serial `lang_window` (L15146) and in `t_rule` (L14616). Documented here, not implemented.

## Checks (26/10/2026, CET)
- Host build strata_spec + 8 tests: rc=0, 0 warnings, 8/8 rc=0 (22:30).
  - lang_knob_test: 21 ok, including the flag-off grid (200 cases, 0 differ), example marker field/comment, non-bool refused, and the repo example file loading marked.
- Python serve.test_strata_lang: 4/4 OK (22:29).
- Syntax HIP/CUDA: rc=0, identical to control (22:30).
- HIP gfx1100 TU-only: rc=0, 131 = 131 warnings, same multiset (22:31:12).
- run_policy_checks N=20000: flag-off IDENTICAL, det reproducible (22:31).
- `git apply --check` rc=0.
- NOT done:
  - full link and gfx1201;
  - prepared scripts: `/workspace/policy-local/hip_build_deferred_v2.sh` and `/workspace/policy-local/hip_build_full_rocm644.sh --bench-window-ended`.
