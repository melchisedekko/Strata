# CommitPackFT selection (licence-filtered manifest), pin fc56fe33

**This is a manifest only. It contains no code text.** It lists IDs, file paths, the language, the licence and numeric lengths. Code, subjects and messages stay local in `commitpackft_fc56fe33/` and are not published.

## Source and pin
- Dataset: `bigcode/commitpackft`, revision `fc56fe33c030c6daa414c2b112c932b8eed085e6` (2023-08-20, "Add licenses"). HF card licence: MIT.
- Files: `data/<lang>/data.jsonl` for python, javascript, java, go, rust, c++, c#, typescript.
  - Each file's sha256 matches the HF LFS oid at this revision (see `commitpackft_fc56fe33/raw_files.sha256`).
  - c# (27,478,215 B) and typescript (14,620,423 B) were present and are included. To drop them, filter on `lang`.
- Tokenizer used for the `*_tokens` columns: `Qwen/Qwen3.5-2B` `tokenizer.json` @ `15852e8c16360a2fea060d615a32b45270f8a8fc` (Apache-2.0).
  - Library: `tokenizers` 0.23.3, `add_special_tokens=False`, raw text with no chat template.
  - No model was loaded or run.

## Filter (per sample)
- Keep a row only if its per-sample `license` field is one of: `mit`, `apache-2.0`, `bsd-2-clause`, `bsd-3-clause`, `isc`, `unlicense`, `cc0-1.0`.
- Every other value was excluded: agpl-3.0, lgpl-2.1, mpl-2.0, epl-1.0, artistic-2.0 and unknown.
- Caveat: the `license` field is the repository-level licence as detected by the dataset authors. It has not been verified file by file.
- No length or size cap has been applied.
- No tune/holdout split has been made; Policy decides that in a hashed run file.

## Columns (`commitpackft_selection_manifest.csv`)
| Column | Meaning |
|---|---|
| `id` | `<commit>:<new_file>`. There are no duplicate (commit, old_file, new_file, lang) keys, so no suffix was needed. |
| `commit`, `old_file`, `new_file`, `lang`, `license` | Copied from the dataset row. |
| `old_bytes`, `new_bytes`, `old_lines`, `new_lines` | Size of the file contents before and after the commit. |
| `changed_lines` | Number of +/- lines in `difflib.unified_diff(old, new, n=0)`. |
| `old_tokens`, `new_tokens`, `subject_tokens`, `message_tokens` | Qwen3.5 token counts. |

## Counts (before -> after the licence filter)
| lang | before | after | old_contents empty (after) |
|---|---|---|---|
| python | 56,025 | 50,152 | 12,004 |
| javascript | 52,989 | 49,776 | 708 |
| java | 20,635 | 18,584 | 6,333 |
| go | 5,004 | 4,673 | 3 |
| rust | 2,996 | 2,809 | 638 |
| c++ | 4,992 | 4,602 | 1,068 |
| c# | 9,346 | 9,033 | 847 |
| typescript | 5,868 | 5,485 | 495 |
| **total** | **157,855** | **145,114** | **22,096** |

Per-licence counts and length percentiles are in `commitpackft_selection_counts.json`.

## Proposed size cap (NOT applied)
Rule: `64 <= old_tokens <= 512 AND 1 <= changed_lines <= 40 AND new_tokens <= 1.5*old_tokens + 256`.

This would remove file creations (empty old file), no-op rows and rewrite-sized rows.

Rows passing the rule:

| lang | rows |
|---|---|
| python | 34,839 |
| javascript | 44,551 |
| java | 11,540 |
| go | 4,285 |
| rust | 1,904 |
| c++ | 3,315 |
| c# | 7,697 |
| typescript | 4,585 |
| **total** | **112,716** |

The passing rows hold 28,145,423 target (`new_contents`) tokens in total, about 250 per row.

Note: in this data `old_tokens` never exceeds 736. Any upper bound of 1024 or more therefore has no effect.

## Integrity
sha256 for the manifest, the counts and this README: `commitpackft_selection.sha256`.
