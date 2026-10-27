#!/usr/bin/env python3
"""proxy CPU, non AMD, llama.cpp non Strata. Inventario H-LANG sulle tracce esistenti secondo LANG_LABEL_RULE.md (sha256 344a793b…).
Legge solo le righe request dei .jsonl sotto /workspace/strata-plus/traces/raw (niente round, niente processi llama).
Uso (dalla root di strata-bench): lang_inventory.py RULE.md RULE_SHA256 OUT_DIR_LOCALE LANG_INVENTORY.json
Dettaglio di implementazione di L2: lo stesso id puo' stare in piu' file di datasets/; se le info-string dei file che lo contengono
non coincidono, L2 non decide (prudente)."""
import json, os, re, sys, glob, hashlib, time, collections
rule, rule_sha, outdir, outj = sys.argv[1:5]
if hashlib.sha256(open(rule, 'rb').read()).hexdigest() != rule_sha: sys.exit('sha della regola diverso: stop')
ROOT = '/workspace/strata-plus/traces/raw'
CANON = {}
for name, al in {'python': 'python py python3', 'cpp': 'cpp c++ cxx hpp cc', 'c': 'c h', 'rust': 'rust rs', 'go': 'go golang', 'java': 'java',
                 'javascript': 'javascript js', 'typescript': 'typescript ts', 'shell': 'bash sh shell zsh', 'json': 'json', 'yaml': 'yaml yml',
                 'cmake': 'cmake', 'markdown': 'markdown md', 'text': 'text txt plaintext'}.items():
    for a in al.split(): CANON[a] = name
def canon(s): s = s.strip().lower(); return CANON.get(s, 'other:' + s)
FENCE = re.compile(r'```[ \t]*([A-Za-z0-9_+#.-]+)')
HEF = re.compile(r'^(Python|JavaScript|Java|Go|CPP|Rust)/\d+')
prompts = collections.defaultdict(set)
for f in sorted(glob.glob('datasets/*.jsonl')):
    for l in open(f):
        try: j = json.loads(l)
        except ValueError: continue
        if 'id' in j and isinstance(j.get('prompt'), str):
            m = FENCE.search(j['prompt']); prompts[j['id']].add(canon(m.group(1)) if m else None)
def label(j):
    d, rid = j.get('domain'), str(j.get('req_id', ''))
    if d == 'code' and rid.startswith('HumanEval/'): return 'L1', 'python'
    if d in ('edit', 'agent_edit'): return 'L1', 'python'
    m = HEF.match(rid) or HEF.match(str(j.get('task_id', '')))
    if m: return 'L1', canon(m.group(1))
    for k in ('lang', 'language'):
        if isinstance(j.get(k), str) and j[k]: return 'L1', canon(j[k])
    s = prompts.get(rid.split('#')[0]) if rid.split('#')[0] in prompts else prompts.get(rid)
    if s and len(s) == 1 and None not in s: return 'L2', next(iter(s))
    return 'L3', 'nl' if d == 'chat' else 'unknown'
files = sorted(f for f in glob.glob(ROOT + '/**/*.jsonl', recursive=True) if '.bak' not in os.path.basename(f))
os.makedirs(outdir, exist_ok=True)
agg = collections.defaultdict(lambda: {'records': 0, 'prompts': set(), 'files': set(), 'output_tokens': 0, 'verify_rounds': 0, 'drafted': 0, 'accepted': 0})
lvl = collections.Counter(); unparsable = 0; nfiles_req = 0
with open(os.path.join(outdir, 'labels_per_request.jsonl'), 'w') as lo:
    for f in files:
        got = False
        for l in open(f, errors='replace'):
            if '"request"' not in l: continue
            try: j = json.loads(l)
            except ValueError: unparsable += 1; continue
            if j.get('type') != 'request': continue
            got = True; L, lang = label(j); d = str(j.get('domain')); lvl[(d, L)] += 1
            a = agg[(d, lang)]; a['records'] += 1; a['prompts'].add((j.get('dataset'), j.get('req_id'))); a['files'].add(f)
            for k in ('output_tokens', 'verify_rounds', 'drafted', 'accepted'): a[k] += j.get(k) or 0
            lo.write(json.dumps({'file': os.path.relpath(f, ROOT), 'req_id': j.get('req_id'), 'rep': j.get('rep'), 'domain': d, 'level': L, 'lang': lang}) + '\n')
        nfiles_req += got
rows = [{'domain': d, 'lang': g, 'records': a['records'], 'distinct_prompts': len(a['prompts']), 'files': len(a['files']),
         'output_tokens': a['output_tokens'], 'verify_rounds': a['verify_rounds'], 'drafted': a['drafted'], 'accepted': a['accepted']}
        for (d, g), a in sorted(agg.items())]
res = {'label': 'proxy CPU, non AMD, llama.cpp non Strata', 'created': time.strftime('%F %T %Z'), 'rule': {'path': rule, 'sha256': rule_sha},
       'tool_sha256': hashlib.sha256(open(__file__, 'rb').read()).hexdigest(), 'root': ROOT, 'jsonl_files_scanned': len(files),
       'files_with_request_records': nfiles_req, 'unparsable_request_lines': unparsable,
       'levels': [{'domain': d, 'level': L, 'records': n} for (d, L), n in sorted(lvl.items())], 'rows': rows,
       'note': 'solo aggregati; etichette per richiesta solo nella cartella locale (non pubblicata)'}
json.dump(res, open(outj, 'w'), indent=1); print(json.dumps({k: res[k] for k in ('jsonl_files_scanned', 'files_with_request_records', 'unparsable_request_lines')}))
