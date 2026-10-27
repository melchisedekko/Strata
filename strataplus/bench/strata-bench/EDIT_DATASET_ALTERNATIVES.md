# Alternatives to the non-publishable-license edit dataset (`edit_np`) for the `edit` domain

Checked on 2026-10-26, 19:45–20:00 CET (UTC+1), by Grok Bot. I used the HF Hub API (`/api/datasets/<id>`, `/commits/main`, raw README at each commit), the HF MCP `hub_repo_details`, and the GitHub REST API (read-only, authenticated). Anything I did not check against a primary source is marked **UNVERIFIED**. This is not legal advice.

What we need: an instruction plus original code, where the model rewrites the code. The licence must allow (a) redistributing derived traces, IDs and metrics, and (b) using the data for fitting or training. The HF card, the GitHub repo and the underlying source data must not contradict each other.

Classes follow LICENSE_INVENTORY.md:
- **PERMISSIVE**: verified permissive at every layer.
- **EXCLUDE**: non-permissive, share-alike, attribution to manage, conflicting licences, or mixed sources that were not verified.
- **UNVERIFIED**: treated the same as EXCLUDE.

## Baseline: why `edit_np` is out

- The dataset's HF card, at the pinned revision (`<revisione non pubblicata>`), has `license: mit`.
- The LICENSE in the dataset's GitHub repo was added later (commit `<commit non pubblicato>`). It is a licence with a restriction on machine-learning use. One clause forbids using the contents as training data for machine-learning models. The GitHub API reports the licence as `NOASSERTION`.
- A related dataset by the same author (HF card MIT) is built with code under the same licence, so it has the same conflict. Classified **EXCLUDE**.

## Ranking

### 1. HumanEvalFix (OctoPack HumanEvalPack): `bigcode/humanevalpack` (recommended)

- **URL**: https://huggingface.co/datasets/bigcode/humanevalpack, pinned at `9a41762f73a8cb23bb5811b73d5aab164efcf378` (2025-08-19, "Convert dataset to Parquet"). Not gated.
- **HF card licence**: `license: mit`. History of the `license:` line across all 72 commits:
  - no README, then no `license` field;
  - `apache-2.0` from b09840f4 (2023-07-22);
  - `mit` from addbb59c (2023-08-11) to today.
  - The only change was from one permissive licence to another, and nothing has changed since 2023-08-11.
- **GitHub repo licence**: https://github.com/bigcode-project/octopack (GitHub API: MIT). `LICENSE` = "MIT License, Copyright (c) 2023 Muennighoff", added in 638da541 (2023-07-30, "Swap to MIT").
  - Before that there was a `LICENSE.md` with Apache-2.0 (79d1f654, 2023-07-22), deleted in 92cc6cbf (2023-07-30).
  - The README section "Licenses" says: "CommitPack, CommitPackFT, HumanEvalPack, and all code are licensed under the MIT License of this repository."
  - Card and repo agree: MIT.
- **Underlying data**:
  - The Python split is OpenAI HumanEval: https://github.com/openai/human-eval, MIT. There is a single LICENSE commit, d321ec0b (2021-07-14).
  - The JS, Java, Go, C++ and Rust splits are derived from HumanEval-X, with fixes documented in `octopack/evaluation/create/humaneval-x/README.md`, whose front matter says `license: apache-2.0`.
  - HumanEval-X upstream is https://github.com/zai-org/CodeGeeX (formerly THUDM): GitHub API Apache-2.0, a single LICENSE commit ba984c64 (2022-09-17), and the README says "Our code is licensed under the Apache-2.0 license". The HF card `zai-org/humaneval-x` says `apache-2.0`.
  - All layers are permissive: MIT plus Apache-2.0. Obligation: keep the MIT and Apache notices if you redistribute the text.
- **Size**: 984 rows, 164 tasks × 6 languages (cpp, go, java, js, python, rust), about 190 KB of parquet per language.
- **Format**: the columns include `buggy_solution`, `canonical_solution`, `declaration`, `prompt`/`docstring`, `bug_type`, `test` and `example_test`. An edit prompt is easy to build: "Fix bugs in `<entry_point>`." plus the buggy code (and optionally the tests), with the fixed code as the target. Works offline. Execution is needed only to measure correctness, not for acceptance traces.
- **Fit**: good. It is a real edit task (rewriting almost identical code), multilingual, and small enough for the benchmark.
- **Risks**:
  - The Python split is HumanEval, which the `code` domain already uses. That means overlap and possible leakage between domains for the classifier and the config table. Mitigations: use only the 5 non-Python languages (820 items), or keep strict ID disjointness and different templates.
  - The bugs are mostly single-point bugs, so outputs are near-copies of the input. Draft acceptance (lookup/n-gram/MTP) could be optimistic compared with larger edits.

### 2. CommitPackFT: `bigcode/commitpackft` (licence-filtered subset)

- **URL**: https://huggingface.co/datasets/bigcode/commitpackft, pinned at `fc56fe33c030c6daa414c2b112c932b8eed085e6` (2023-08-20, "Add licenses"). Not gated.
- **HF card licence**: `license: mit`. History of the `license:` line across all 30 commits:
  - no README, then no field;
  - `apache-2.0` from 239b2459 (2023-07-22);
  - `mit` from 9a0b126b (2023-08-11, "Change to MIT License").
  - The section "Licensing Information" says: "Each sample comes from a code repository with a permissive license. The license is provided by the `license` field."
- **GitHub repo licence**: octopack is MIT (same history as above), and its README confirms MIT for CommitPackFT.
- **Underlying data**: **not uniformly permissive, which contradicts the card's "permissive" claim.** I counted the `license` field over 6 languages (142,641 samples):
  - 91.6% are mit, apache-2.0, bsd-3-clause, bsd-2-clause, isc, unlicense or cc0-1.0;
  - the rest are agpl-3.0 (7,499), lgpl-2.1 (1,796), mpl-2.0 (1,785), epl-1.0 (619), artistic-2.0 (170) and unknown (176);
  - Python alone: 56,025 rows, 89.5% permissive, agpl-3.0 = 4,380.
  - The field is the repo-level licence as detected by the authors (paper arXiv 2308.07124). I did **not** verify it file by file (**UNVERIFIED** per sample).
  - Per-language counts (permissive / total): c++ 4,602/4,992; go 4,673/5,004; java 18,584/20,635; javascript 49,776/52,989; python 50,152/56,025; rust 2,809/2,996.
- **Size**: 702,062 samples, 1,545 MB, 277 languages (card table).
- **Format**: `subject`/`message` (the commit message used as the instruction) + `old_contents` → `new_contents`, plus `commit`, `old_file`, `new_file`, `repos`, `license`. This is exactly instruction + code → edited code. Works offline, no harness.
- **Fit**: good and realistic (real edits, many languages, large pool to sample from). Needs filtering: `license ∈ {mit, apache-2.0, bsd-2-clause, bsd-3-clause, isc, unlicense, cc0-1.0}`, a length cap, and messages that look like instructions.
- **Risks**:
  - Mixed licences inside the dataset, so the filter is mandatory and per-sample licences are not independently verified.
  - Attribution obligations (MIT/BSD/Apache NOTICE) if you redistribute text. Publishing only IDs (`commit` + `old_file`) and metrics avoids this.
  - Noisy commit messages; possible personal data in commits (names/emails in code or comments).
  - The parent `bigcode/commitpack` (4 TB, card MIT, same Apache→MIT history 2023-07-22 → 2023-08-11, last commit 5eee2c84 on 2025-02-04) has the same `license` field and the same issue.
  - Derivative `cassanof/CodeEditSearch` (card MIT, has a `license` field) inherits the same issue. Not analysed further.

### 3. Aider polyglot benchmark (Exercism): `Aider-AI/polyglot-benchmark`

- **URL**: https://github.com/Aider-AI/polyglot-benchmark, HEAD 7e0611e7 (2024-12-22). It is not on HF: `Aider-AI/polyglot-benchmark` does not exist as an HF dataset.
- **Repo licence**: **no LICENSE file.** The GitHub API returns `license: null`, and the root contains only README.md and the language directories. The README says: "All exercise content is copyright © Exercism … used in accordance with Exercism's open source licenses." The harness lives in https://github.com/Aider-AI/aider (Apache-2.0).
- **Underlying data**: the Exercism tracks `exercism/{cpp,go,java,javascript,python,rust}` and `exercism/problem-specifications` are all MIT according to the GitHub API. `exercism/python` LICENSE = "MIT License, Copyright (c) 2021 Exercism". Its LICENSE history is MIT since 2014-02-28 (3a288c49) with copyright updates only. I checked the history only for python; for the other tracks I checked only the current licence.
- **Size**: 225 exercises (cpp 26, go 39, java 47, javascript 49, python 34, rust 30), counted from the git tree.
- **Format**: `.docs/instructions.md` + a stub file → solution, with tests and a reference solution in `.meta/example.*`. It is more "fill in a stub" than "edit existing code" (the stubs are almost empty). Prompts work offline; tests need language toolchains.
- **Fit**: medium-low for the edit domain. It also overlaps with the `code` (generation) domain.
- **Risk**: the aggregating repo has no licence. Better to take the files directly from the MIT Exercism repos and keep the MIT notice.

## Other candidates checked (not recommended)

| Dataset | URL | HF card | GitHub repo | Underlying data | Size / format | Verdict |
|---|---|---|---|---|---|---|
| related dataset by the same author | `<URL non pubblicato>` | MIT (card sha `<sha non pubblicato>`) | code under the same licence as `edit_np`: ML-use restriction | CommitPackFT (mixed, see above) | not published | **EXCLUDE** (conflict, as for `edit_np`). Its multilingual variant: card without a licence |
| InstructCoder | https://huggingface.co/datasets/likaixin/InstructCoder | **no licence** (sha 6a778a72); the card asks for compliance with the licences of the LLMs used | https://github.com/qishenghu/InstructCoder MIT (single LICENSE commit 58c6fa96, 2023-05-21) | generated by ChatGPT (README) + GitHub seed commits (634 seed + 134 test) with unverified licences | 114,239 triplets, instruction+input→output | **EXCLUDE** (card vs repo mismatch, terms of the generating model, unverified seeds) |
| CodeEditorBench | https://huggingface.co/datasets/m-a-p/CodeEditorBench | apache-2.0 (sha 9bd3f759) | https://github.com/CodeEditorBench/CodeEditorBench Apache-2.0, but commit 1b9cc1e7 (2024-04-04) added "The content within the evaluation module adheres to the GPL-2.0 license" (HUSTOJ) | "five sources" of coding problems (README), not listed per item. The card's disclaimer asks for reports of copyright violations | 8 jsonl (debug/polish/switch/translate × primary/plus) | **EXCLUDE / UNVERIFIED** (sources not verified; the GPL-2.0 part applies to the harness) |
| NoFunEval | https://huggingface.co/datasets/ManavSinghal157/NoFunEval | MIT (sha d04f68f5) | https://github.com/microsoft/NoFunEval MIT (LICENSE 55dd26f0, 2024-02-19) | `source_code` from various GitHub repos (e.g. `rcbops/glance-buildpackage`, Apache header), PIE codebase and CodeQL; per-repo licences not verified | 397 edit items (latency 47, maintainability 145, resource_util 51, runtime_efficiency 113, security 41) + 164 humanevalclassify | **UNVERIFIED** (good format; the underlying data is mixed) |
| SWE-bench / Lite / Verified | https://huggingface.co/datasets/princeton-nlp/SWE-bench (also SWE-bench/SWE-bench_Lite, b0dde109 2026-08-16) | **no licence** on the cards | https://github.com/SWE-bench/SWE-bench MIT | 12 repos: django, scikit-learn, astropy, flask, seaborn BSD-3; requests, xarray Apache-2.0; pytest MIT; **pylint GPL-2.0**; sympy, sphinx NOASSERTION; matplotlib not detected | 2,294 / 300 / 500; issue + repo → patch, needs a repo checkout (network) | **EXCLUDE** (card without a licence, GPL-2.0 component, poor fit offline) |
| CodeReviewer | https://zenodo.org/record/6900648 | (not on HF; derived HF copies not checked) | https://github.com/microsoft/CodeBERT MIT | Zenodo: **CC-BY-4.0**; code from GitHub repos not verified | ~4.8 GB zip (Code_Refinement 1.17 GB); old code + review comment → refined code | **EXCLUDE** (attribution to manage, as for MBPP CC-BY-4.0; unverified sources) |
| CoEdPilot | https://huggingface.co/datasets/code-philia/CoEdPilot-generator | **no licence** (sha ef45c1f4; `-line-locator` is MIT) | https://github.com/code-philia/CoEdPilot: GitHub API licence `null` | GitHub commits (unverified) | jsonl go/java/js/... | **EXCLUDE** |
| EditEval | https://huggingface.co/datasets/bzz2/EditEval | **cc-by-nc-sa-4.0** | — | prose editing (asset, jfleg, iterater…), not code | — | **EXCLUDE** (NC/SA, wrong domain) |
| NextCoderDataset | https://huggingface.co/datasets/microsoft/NextCoderDataset | MIT (sha 924e23fa) | https://github.com/microsoft/NextCoder (GitHub licence not checked) | generated with GPT-4o and Llama-3.3-70B-Instruct from StarCoderData (card) → the terms of the generating models and of StarCoderData apply (**UNVERIFIED**) | ~381k samples, 8 languages, instruction + code → edit | **UNVERIFIED** (layered terms) |
| zed-industries/zeta | https://huggingface.co/datasets/zed-industries/zeta | apache-2.0 (sha 0f41422b) | not checked | edit predictions "pulled from Snowflake" (Zed telemetry); code provenance and consent **UNVERIFIED** | 418 train / 33 eval / 132 dpo (md files) | **UNVERIFIED**; format is next-edit prediction, not instruction+code |

## Recommendation

1. Replace `edit_np` with **HumanEvalFix** (`bigcode/humanevalpack` @9a41762f). Card MIT = repo MIT; underlying data MIT (HumanEval) + Apache-2.0 (HumanEval-X); no restrictive clauses; works offline.
   - To avoid overlap with the HumanEval `code` domain, use only the **5 non-Python languages (820 items)**.
   - Template: "Fix bugs in `<entry_point>`." + `declaration`+`buggy_solution`.
   - IDs: `HumanEvalFix/<Lang>/<N>`.
   - Keep the MIT and Apache-2.0 notices in the inventory.
2. If you need more realistic edits (larger, real commits), add a **CommitPackFT subset** filtered on `license ∈ {mit, apache-2.0, bsd-2-clause, bsd-3-clause, isc, unlicense, cc0-1.0}`. Publish only IDs (`commit`+`old_file`) and metrics, and record that the `license` field is the dataset's own repo-level label (not verified file by file).

## Sources (all checked 2026-10-26 CET)

- HF API: `https://huggingface.co/api/datasets/{bigcode/humanevalpack,bigcode/commitpackft,bigcode/commitpack,likaixin/InstructCoder,m-a-p/CodeEditorBench,ManavSinghal157/NoFunEval,princeton-nlp/SWE-bench,SWE-bench/SWE-bench_Lite,microsoft/NextCoderDataset,zed-industries/zeta,code-philia/CoEdPilot-generator,bzz2/EditEval,zai-org/humaneval-x}` and `/commits/main` (plus the related dataset by the same author, `<URL non pubblicato>`)
- https://github.com/bigcode-project/octopack/blob/main/LICENSE ; commits 638da541, 92cc6cbf, 79d1f654
- https://github.com/openai/human-eval/blob/master/LICENSE
- https://github.com/zai-org/CodeGeeX/blob/main/LICENSE
- LICENSE of the dataset's GitHub repo, commit `<commit non pubblicato>` (`<URL not published>`)
- https://github.com/Aider-AI/polyglot-benchmark ; https://github.com/exercism/python/blob/main/LICENSE
- https://github.com/CodeEditorBench/CodeEditorBench/commit/1b9cc1e7
- https://github.com/microsoft/NoFunEval ; https://github.com/qishenghu/InstructCoder ; https://github.com/SWE-bench/SWE-bench
- https://zenodo.org/api/records/6900648
- CommitPackFT licence counts: computed locally from `data/{python,javascript,java,go,rust,c++}/data.jsonl` @fc56fe33
