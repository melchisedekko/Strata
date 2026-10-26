"""agent_v12: adapter che riusa SYSTEM/TOOLS/SESSIONS/turns() di /workspace/Strata/tools/agent_turns_bench.py (import, nessuna copia
del contenuto) e rende ogni turno col chat template del GGUF target (tokenizer.chat_template, enable_thinking non definito ->
'<think>\\n\\n</think>\\n\\n' come in v1.1). Ogni turno e' un prompt completo (il prefisso del turno precedente + chiamata/risultato tool
fissi, NON l'output del modello), quindi e' marcato raw=1: il proxy v12 lo tokenizza cosi' com'e' senza concatenare l'output precedente.
Nessuna metrica. proxy CPU, non AMD."""
import json, sys, hashlib, subprocess
sys.path.insert(0, '/workspace/llama.cpp/gguf-py'); sys.path.insert(0, '/workspace/Strata/tools')
import jinja2
from gguf import GGUFReader
import agent_turns_bench as atb
MODEL, OUT, META = sys.argv[1:4]
f = GGUFReader(MODEL).fields['tokenizer.chat_template']; tmpl_src = bytes(f.parts[f.data[0]]).decode()
env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, extensions=['jinja2.ext.loopcontrols'])
def rex(m): raise jinja2.TemplateError(m)
env.globals['raise_exception'] = rex
tmpl = env.from_string(tmpl_src)
rows = []; files = {}
for tag, msgs in atb.turns():
    name, i = tag.rsplit('.', 1)
    m2 = []
    for m in msgs:
        m = dict(m)
        if 'tool_calls' in m:
            m['tool_calls'] = [{**tc, 'function': {**tc['function'], 'arguments': json.loads(tc['function']['arguments'])}} for tc in m['tool_calls']]
        m2.append(m)
    text = tmpl.render(messages=m2, tools=atb.TOOLS, add_generation_prompt=True)
    rows.append({'id': f'agent_v12-{name}#t{i}', 'category': 'agent_strata', 'source': 'strata-repo', 'split': 'agent_v12',
                 'session_id': f'agent_v12-{name}', 'turn': i, 'raw': '1', 'prompt': text,
                 'license': 'MIT (Strata LICENSE, Copyright (c) 2026 Niko1221 and the Strata contributors) per i contenuti dei file del repo; SYSTEM/task/TOOLS da tools/agent_turns_bench.py dello stesso repo'})
    for s in atb.SESSIONS:
        if s[0] == name:
            for tool, arg, _ in s[1][:0] or s[2][:int(i) + 1]:
                if tool == 'read_file': files[arg] = hashlib.sha256(open(f'/workspace/Strata/{arg}', 'rb').read()).hexdigest()
with open(OUT, 'w') as o:
    for r in rows: o.write(json.dumps(r, ensure_ascii=False) + '\n')
rev = subprocess.run(['git', '-C', '/workspace/Strata', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(['git', '-C', '/workspace/Strata', 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
json.dump({'label': 'proxy CPU, non AMD', 'split': 'agent_v12', 'strata_rev': rev, 'strata_worktree_clean': not dirty,
           'agent_turns_bench_sha256': hashlib.sha256(open('/workspace/Strata/tools/agent_turns_bench.py', 'rb').read()).hexdigest(),
           'license_file_sha256': hashlib.sha256(open('/workspace/Strata/LICENSE', 'rb').read()).hexdigest(),
           'chat_template_source': f'{MODEL} tokenizer.chat_template', 'chat_template_sha256': hashlib.sha256(tmpl_src.encode()).hexdigest(),
           'enable_thinking': 'non definito (default template -> blocco think vuoto)',
           'deviations_from_agent_turns_bench': 'greedy (temp 0) invece di temp 1/top-p 0.95/top-k 20/seed; reasoning_effort high non applicato (thinking vuoto come v1.1); template del GGUF qwen35-2b invece del template del pack Strata; repo a ' + rev + ' (docstring cita 0.1.41)',
           'read_files_sha256': files, 'n_turns': len(rows), 'chars': {r['id']: len(r['prompt']) for r in rows}}, open(META, 'w'), indent=1)
print(len(rows), 'turni;', 'max chars', max(len(r['prompt']) for r in rows))
