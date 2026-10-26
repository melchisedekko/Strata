#!/usr/bin/env python3
"""CommitPackFT @fc56fe33 per-sample licence filter + length stats. No model is run.
Tokens: Qwen/Qwen3.5-2B tokenizer.json @15852e8c (tokenizers lib, no special tokens added)."""
import json, csv, os, sys, difflib, collections, statistics
os.environ.setdefault("RAYON_NUM_THREADS", "1")
from tokenizers import Tokenizer
D = "/workspace/strata-bench/datasets/commitpackft_fc56fe33"
LANGS = ["python", "javascript", "java", "go", "rust", "c++", "c#", "typescript"]
ALLOW = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc", "unlicense", "cc0-1.0"}
tok = Tokenizer.from_file(f"{D}/tokenizer/tokenizer.json")
def nt(s): return len(tok.encode(s, add_special_tokens=False).ids) if s else 0
os.makedirs(f"{D}/selected", exist_ok=True)
before = collections.Counter(); after = collections.Counter()
lic_by_lang = collections.defaultdict(collections.Counter)
rows_out = []; seen = collections.Counter()
for lang in LANGS:
    with open(f"{D}/raw/{lang}/data.jsonl") as f, open(f"{D}/selected/{lang}.jsonl", "w") as g:
        for line in f:
            r = json.loads(line)
            lic = r.get("license"); lic_by_lang[lang][lic] += 1; before[lang] += 1
            if lic not in ALLOW: continue
            after[lang] += 1
            old, new = r.get("old_contents") or "", r.get("new_contents") or ""
            ol, nl = old.splitlines(), new.splitlines()
            ch = 0
            for d in difflib.unified_diff(ol, nl, lineterm="", n=0):
                if (d.startswith("+") or d.startswith("-")) and not (d.startswith("+++") or d.startswith("---")): ch += 1
            st = dict(old_bytes=len(old.encode()), new_bytes=len(new.encode()), old_lines=len(ol), new_lines=len(nl),
                      changed_lines=ch, old_tokens=nt(old), new_tokens=nt(new), subject_tokens=nt(r.get("subject") or ""),
                      message_tokens=nt(r.get("message") or ""))
            key = (r["commit"], r["old_file"], r["new_file"], lang); seen[key] += 1
            rid = f"{r['commit']}:{r['new_file']}" + (f"#{seen[key]}" if seen[key] > 1 else "")
            g.write(json.dumps({"id": rid, **r, "_stats": st}, ensure_ascii=False) + "\n")
            rows_out.append({"id": rid, "commit": r["commit"], "old_file": r["old_file"], "new_file": r["new_file"],
                             "lang": lang, "license": lic, **st})
    print(lang, before[lang], after[lang], flush=True)
cols = ["id","commit","old_file","new_file","lang","license","old_bytes","new_bytes","old_lines","new_lines",
        "changed_lines","old_tokens","new_tokens","subject_tokens","message_tokens"]
with open("/workspace/strata-bench/datasets/commitpackft_selection_manifest.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_MINIMAL); w.writeheader(); w.writerows(rows_out)
def q(v, p): v = sorted(v); return v[min(len(v)-1, int(p*len(v)))]
agg = {"pin": "bigcode/commitpackft@fc56fe33c030c6daa414c2b112c932b8eed085e6", "allowed_licenses": sorted(ALLOW),
       "per_language": {}, "duplicate_keys": sum(1 for k, c in seen.items() if c > 1)}
for lang in LANGS:
    sub = [r for r in rows_out if r["lang"] == lang]
    e = {"rows_before": before[lang], "rows_after": after[lang], "licenses_before": dict(lic_by_lang[lang].most_common()),
         "licenses_after": dict(collections.Counter(r["license"] for r in sub).most_common())}
    for k in ["old_tokens", "new_tokens", "changed_lines", "old_bytes"]:
        v = [r[k] for r in sub]
        e[k] = {"min": min(v), "p10": q(v,.1), "p25": q(v,.25), "p50": q(v,.5), "p75": q(v,.75), "p90": q(v,.9),
                "p99": q(v,.99), "max": max(v), "mean": round(statistics.mean(v), 1)}
    agg["per_language"][lang] = e
agg["totals"] = {"rows_before": sum(before.values()), "rows_after": sum(after.values())}
# candidate caps (proposal only; not applied)
caps = {}
for lo, hi in [(64, 1024), (128, 1024), (128, 1536), (128, 2048), (256, 2048)]:
    for chmax in [None, 40]:
        name = f"old_tokens[{lo},{hi}]" + (f"&changed_lines<={chmax}" if chmax else "") + "&new_tokens<=old_tokens*1.5+256"
        ok = [r for r in rows_out if lo <= r["old_tokens"] <= hi and r["new_tokens"] <= r["old_tokens"]*1.5+256
              and (chmax is None or r["changed_lines"] <= chmax)]
        c = collections.Counter(r["lang"] for r in ok)
        caps[name] = {"total": len(ok), "per_language": {l: c[l] for l in LANGS},
                      "sum_new_tokens": sum(r["new_tokens"] for r in ok), "sum_old_tokens": sum(r["old_tokens"] for r in ok)}
agg["candidate_caps_not_applied"] = caps
json.dump(agg, open("/workspace/strata-bench/datasets/commitpackft_selection_counts.json", "w"), indent=1)
print("done", agg["totals"], "dupkeys", agg["duplicate_keys"])
