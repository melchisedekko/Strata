# strataplus-LANG-knob-v1.patch

- sha256: `131fc71a0d33655aa67bead54dc6bc92d761e8a5b41c0a09cd42d3281d4e9724`
- Base: b24c6a1d + strataplus-H1-arbiter-v1.patch (= local commit e959072a). It does NOT apply on b24c6a1d alone
  (CMakeLists.txt). Local commit `4c4a7002`.
- Apply: `git apply strataplus-H1-arbiter-v1.patch && git apply strataplus-LANG-knob-v1.patch`. Both checks rc=0, and
  the resulting tree equals 4c4a7002.
- 8 files, +544/-3. No data, no secrets, no edit_np. The example table only has placeholder numbers (format only).

## What it adds (OFF by default = upstream)
- Startup: `--spec-lang-table FILE` or `STRATA_SPEC_LANG_TABLE=FILE` (the flag wins). Loaded and validated before the
  model load. Error -> exit 1.
- Request (serve GEN): `strata_lang=<name>`. Unknown or missing -> global default. No language detection.
- Table schema "strataplus.lang_knob.v1": per language, `spec_min_p` and `t_rule` default | min_p (`t_max`) | fixed (`t`).
  T <= S_mtp, kMaxT=8. S, S_mtp and the lookup cap are never changed.
- spec_min_p precedence: request > table > `--spec-min-p`.
- Limits: serial GEN loop only (not BGEN, not pipeline T, not non-first windows with STRATA_SPEC_COST=1).
  SYCL "ignorata su SYCL". qwen35moe warning. serve/server.py does not forward strata_lang.
- Docs: docs/strataplus_lang_knob.md. Example: strataplus/tests/lang_table_example.json. Test: ctest lang_knob_test.

## Checks (CET 26/10/2026)
- Host build strata_spec + 9 tests: rc=0, 0 warnings. 9/9 PASS. lang_knob_test 18 ok, flag-off grid 200 cases, 0 differ (22:18).
- Syntax check HIP/CUDA generate.cpp: rc=0, warnings identical to the control (22:18).
- HIP gfx1100 TUs generate.cpp.o + strata_spec: rc=0, 131 warnings = control, no new warnings (22:18:27-22:19:21).
- run_policy_checks.sh on the final tree: rc=0, flag-off sha256 identical, det ALL IDENTICAL.
- Same limits as H1: full link not done, gfx1201 not supported by the box toolchain.
