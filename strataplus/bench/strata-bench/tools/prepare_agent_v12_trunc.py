"""agent_v12 a ctx 49152 (decisione Lead): come prepare_agent_v12.py (stesso import di agent_turns_bench, stesso template GGUF), ma ogni
turno che supera il budget B = 49152 - 128 (n_predict) - 7 (dmax) - 4 (margine del proxy, proxy/llama_spec_trace_v12.cpp:170) = 49013 token viene
troncato togliendo le coppie (assistant tool_call, tool result) piu' VECCHIE; system + task restano sempre. Se anche con la sola coppia
corrente il prompt supera B, il contenuto del tool result corrente viene accorciato tenendo le prime righe (stessa convenzione di
agent_turns_bench.tool_result: '... (truncated: lines 1-N of M)'), N massimo che entra in B. Token contati con llama-tokenize (vocab-only)
sul testo templato, come il proxy v12 in raw mode. Metadati di troncamento in ogni riga. proxy CPU, non AMD."""
import json, sys, hashlib, subprocess, tempfile, os
sys.path.insert(0, '/workspace/llama.cpp/gguf-py'); sys.path.insert(0, '/workspace/Strata/tools')
import jinja2
from gguf import GGUFReader
import agent_turns_bench as atb
MODEL, OUT, META = sys.argv[1:4]
CTX = 49152; B = CTX - 128 - 7 - 4
TOK = '/workspace/llama.cpp/build/bin/llama-tokenize'
f = GGUFReader(MODEL).fields['tokenizer.chat_template']; tmpl_src = bytes(f.parts[f.data[0]]).decode()
env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, extensions=['jinja2.ext.loopcontrols'])
def rex(m): raise jinja2.TemplateError(m)
env.globals['raise_exception'] = rex
tmpl = env.from_string(tmpl_src)
LIC = 'MIT (Strata LICENSE, Copyright (c) 2026 Niko1221 and the Strata contributors) per i contenuti dei file del repo; SYSTEM/task/TOOLS da tools/agent_turns_bench.py dello stesso repo'
def fix(m):
    m = dict(m)
    if 'tool_calls' in m:
        m['tool_calls'] = [{**tc, 'function': {**tc['function'], 'arguments': json.loads(tc['function']['arguments'])}} for tc in m['tool_calls']]
    return m
def render(msgs): return tmpl.render(messages=[fix(m) for m in msgs], tools=atb.TOOLS, add_generation_prompt=True)
cache = {}
def ntok(text):
    h = hashlib.sha256(text.encode()).hexdigest()
    if h not in cache:
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.txt') as t: t.write(text); p = t.name
        r = subprocess.run([TOK, '-m', MODEL, '-f', p, '--ids', '--show-count', '--log-disable'], capture_output=True, text=True, errors='replace'); os.unlink(p)
        cache[h] = int([l for l in r.stdout.splitlines() if l.startswith('Total number of tokens:')][0].split(':')[1])
    return cache[h]
rows = []
for tag, msgs in atb.turns():
    name, i = tag.rsplit('.', 1); i = int(i)
    head, pairs = msgs[:2], [msgs[2 + 2 * k: 4 + 2 * k] for k in range((len(msgs) - 2) // 2)]
    orig = ntok(render(msgs)); dropped = []; cut = None
    keep = list(range(len(pairs)))
    while ntok(render(head + sum((pairs[k] for k in keep), []))) > B and len(keep) > 1:
        dropped.append(keep.pop(0))
    text = render(head + sum((pairs[k] for k in keep), []))
    if ntok(text) > B:   # solo la coppia corrente e ancora troppo lunga: accorcia il tool result corrente (prime N righe)
        last = [dict(m) for m in pairs[keep[0]]]; lines = last[1]['content'].split('\n'); M = len(lines); lo, hi = 0, M
        def mk(N):
            l2 = [dict(m) for m in last]; l2[1]['content'] = '\n'.join(lines[:N]) + f'\n... (truncated: lines 1-{N} of {M})'; return render(head + l2)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if ntok(mk(mid)) <= B: lo = mid
            else: hi = mid - 1
        text = mk(lo); cut = {'step': keep[0], 'lines_kept': lo, 'lines_total': M}
    kept = ntok(text)
    assert kept <= B, (tag, kept)
    tr = {'ctx_limit': CTX, 'token_budget': B, 'original_tokens': orig, 'kept_tokens': kept, 'truncated': bool(dropped or cut),
          'dropped_turns': dropped, 'dropped_turns_note': 'indici (0-based) delle coppie assistant tool_call + tool result tolte, dalle piu\' vecchie; system+task sempre tenuti',
          'tool_result_cut': cut}
    rows.append({'id': f'agent_v12-{name}#t{i}', 'category': 'agent_strata', 'source': 'strata-repo', 'split': 'agent_v12',
                 'session_id': f'agent_v12-{name}', 'turn': i, 'raw': '1', 'prompt': text, 'license': LIC, 'truncation': tr})
    print(rows[-1]['id'], orig, '->', kept, 'dropped', dropped, 'cut', cut, flush=True)
with open(OUT, 'w') as o:
    for r in rows: o.write(json.dumps(r, ensure_ascii=False) + '\n')
rev = subprocess.run(['git', '-C', '/workspace/Strata', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(['git', '-C', '/workspace/Strata', 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
json.dump({'label': 'proxy CPU, non AMD', 'split': 'agent_v12', 'ctx_limit': CTX, 'token_budget': B, 'strata_rev': rev, 'strata_worktree_clean': not dirty,
           'agent_turns_bench_sha256': hashlib.sha256(open('/workspace/Strata/tools/agent_turns_bench.py', 'rb').read()).hexdigest(),
           'license_file_sha256': hashlib.sha256(open('/workspace/Strata/LICENSE', 'rb').read()).hexdigest(), 'license': LIC,
           'chat_template_sha256': hashlib.sha256(tmpl_src.encode()).hexdigest(),
           'deviations_from_agent_turns_bench': 'greedy (temp 0) invece di temp 1/top-p 0.95/top-k 20/seed; reasoning_effort high non applicato (thinking vuoto come v1.1); template del GGUF qwen35-2b invece del template del pack Strata; repo a ' + rev + ' (docstring cita 0.1.41); troncamento a ctx 49152',
           'truncation': {r['id']: r['truncation'] for r in rows}, 'n_turns': len(rows), 'n_truncated': sum(r['truncation']['truncated'] for r in rows)}, open(META, 'w'), indent=1)
