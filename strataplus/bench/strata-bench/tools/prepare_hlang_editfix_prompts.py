#!/usr/bin/env python3
"""proxy CPU, non AMD, llama.cpp non Strata. Prompt delle tracce H-LANG/edit-fix (run_hlang_editfix_traces_v1).
Legge lo split di Policy (run_hlang_editfix.json: riferimento di pre-registrazione sha256 bbb9eb22..., oppure copia pubblica dd1b8ee8...;
le due copie differiscono solo alla riga 291, nota di pubblicazione) e i 5 parquet HumanEvalFix (bigcode/humanevalpack @9a41762f, MIT).
Scrive datasets/hlang_editfix_tune.jsonl (40 N x 5 linguaggi = 200) e datasets/hlang_editfix_holdout.jsonl (200), formato del tracer
{"id","category","source","prompt"} + campi informativi (lang, N, split, fold) che il tracer ignora. Le 84 N di riserva NON si scrivono.
Etichette di lingua: LANG_LABEL_RULE.md (sha256 344a793b...): L1 = prefisso del task_id; si riporta anche L2 (prima info-string di fence del prompt)
e l'accordo L1/L2. Nessun modello, nessuna traccia.
Uso: python prepare_hlang_editfix_prompts.py <outdir> [--check]   (--check: rigenera in memoria e confronta con i file esistenti, exit 1 se diversi)
Serve pyarrow (venv /tmp/venv_pa sul box)."""
import hashlib, json, os, re, sys
REF = ('/workspace/lic_rm/orig_2026-10-27/workspace/strata-policy/replay/run_hlang_editfix.json',
       'bbb9eb220f5a6aa5e95f15f05b85d9daf2e1684e7da86506a17cca4b8f103dde')
PUB = ('/workspace/strata-policy/replay/run_hlang_editfix.json', 'dd1b8ee8a9932331d15244e220791f975c5800fe224d16778ab70d8a85661d0e')
RULE = ('/workspace/strata-bench/LANG_LABEL_RULE.md', '344a793b42fb7cfc100698177a3b5207e6686dba591064f205d2c13471da49a3')
DS = '/workspace/strata-bench/datasets/humanevalfix_9a41762f'
PARQ = {'js': '52d6aada9ff62c22ba139aaa64431cca461fbca3cb0625521a988ffeef250855', 'java': '0be942d715894e3b350149f1cde6593e95eda495aa4bd1750f09428c0b3e3e9c',
        'go': '5cbb0e8152b5c9d2b595a1fa9d540c87cde7a306e9fc7f63febe24825bc20c74', 'cpp': 'fd2eed15063bf883952fb3b0a23a372eeaa9b9e58932a496667a0c2595145779',
        'rust': '02570ed6a11d8801d26a9aae0db87cdc0fc6f4a7eb68adb3a9e37fb4f752da57'}
# config -> (prefisso task_id, nome nel testo, info-string del fence, nome canonico LANG_LABEL_RULE sez. 3)
LANG = {'js': ('JavaScript', 'JavaScript', 'javascript', 'javascript'), 'java': ('Java', 'Java', 'java', 'java'), 'go': ('Go', 'Go', 'go', 'go'),
        'cpp': ('CPP', 'C++', 'cpp', 'cpp'), 'rust': ('Rust', 'Rust', 'rust', 'rust')}
ORDER = ['js', 'java', 'go', 'cpp', 'rust']
CANON = {'python': 'python', 'py': 'python', 'python3': 'python', 'cpp': 'cpp', 'c++': 'cpp', 'cxx': 'cpp', 'hpp': 'cpp', 'cc': 'cpp',
         'c': 'c', 'h': 'c', 'rust': 'rust', 'rs': 'rust', 'go': 'go', 'golang': 'go', 'java': 'java', 'javascript': 'javascript', 'js': 'javascript',
         'typescript': 'typescript', 'ts': 'typescript'}
L1 = {'Python': 'python', 'JavaScript': 'javascript', 'Java': 'java', 'Go': 'go', 'CPP': 'cpp', 'Rust': 'rust'}
# Template (scelta di Bench, ispirato a HumanEvalFixTests di OctoPack: dichiarazione + soluzione buggy + test; istruzione "Fix bugs in ...").
TEMPLATE = 'Fix bugs in `{entry}`. The following {name} code contains a bug. Reply with the full fixed code in one code block.\n\n```{info}\n{code}```\n\nTests:\n\n```{info}\n{test}```'
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def load_split():
    got = {}
    for p, h in (REF, PUB):
        if os.path.exists(p):
            s = sha(p)
            if s != h: sys.exit(f'ERRORE: sha256 di {p} = {s}, atteso {h}')
            got[h] = json.load(open(p))['split']
    if not got: sys.exit('ERRORE: nessuna copia di run_hlang_editfix.json trovata')
    if len(got) == 2 and got[REF[1]] != got[PUB[1]]: sys.exit('ERRORE: split diverso tra riferimento e copia pubblica: STOP')
    sp = got.get(REF[1]) or got[PUB[1]]
    used = REF if REF[1] in got else PUB
    T, H, R = sp['tune_N'], sp['holdout_N'], sp['reserve_N']
    assert len(T) == 40 and len(H) == 40 and len(R) == 84 and not (set(T) & set(H)) and set(T) | set(H) | set(R) == set(range(164))
    assert sorted(sum(sp['tune_folds_N'], [])) == sorted(T) and len(sp['tune_folds_N']) == 5
    return sp, used, sorted(got)
def l2(prompt):
    m = re.search(r'```([^\s`]+)', prompt)
    if not m: return None
    i = m.group(1).lower(); return CANON.get(i, 'other:' + i)
def build():
    import pyarrow.parquet as pq
    if sha(RULE[0]) != RULE[1]: sys.exit('ERRORE: sha256 di LANG_LABEL_RULE.md diverso')
    sp, used, seen = load_split()
    fold = {n: k for k, f in enumerate(sp['tune_folds_N']) for n in f}
    rows = {}
    for c in ORDER:
        p = f'{DS}/{c}/test-00000-of-00001.parquet'
        if sha(p) != PARQ[c]: sys.exit(f'ERRORE: sha256 di {p} diverso')
        for r in pq.read_table(p).to_pylist():
            pre, n = r['task_id'].split('/'); assert pre == LANG[c][0]; rows[(c, int(n))] = r
    out = {'tune': [], 'holdout': []}; agree = {'tune': [0, 0], 'holdout': [0, 0]}
    for part, Ns in (('tune', sp['tune_N']), ('holdout', sp['holdout_N'])):
        for n in sorted(Ns):
            for c in ORDER:
                r = rows[(c, n)]; pre, name, info, canon = LANG[c]
                pr = TEMPLATE.format(entry=r['entry_point'], name=name, info=info, code=r['declaration'] + r['buggy_solution'], test=r['test'])
                lab1 = L1[r['task_id'].split('/')[0]]; lab2 = l2(pr)
                agree[part][0] += lab1 == lab2; agree[part][1] += 1
                out[part].append({'id': r['task_id'], 'category': 'edit-fix', 'source': 'humanevalfix', 'prompt': pr, 'lang': lab1, 'N': n,
                                  'split': part, **({'fold': fold[n]} if part == 'tune' else {})})
    return out, agree, sp, used, seen
def main():
    od = sys.argv[1]; check = '--check' in sys.argv
    out, agree, sp, used, seen = build()
    for part in ('tune', 'holdout'):
        txt = ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in out[part]); fn = f'{od}/hlang_editfix_{part}.jsonl'
        if check:
            if open(fn).read() != txt: sys.exit(f'ERRORE: {fn} non coincide con la rigenerazione')
        else:
            open(fn, 'w').write(txt)
    per = {p: {LANG[c][3]: sum(1 for x in out[p] if x['lang'] == LANG[c][3]) for c in ORDER} for p in out}
    meta = {'label': 'proxy CPU, non AMD, llama.cpp non Strata', 'split_source': used[0], 'split_source_sha256': used[1], 'copies_found_sha256': seen,
            'seed': sp['seed'], 'tune_N': sorted(sp['tune_N']), 'holdout_N': sorted(sp['holdout_N']), 'reserve_N_count': len(sp['reserve_N']),
            'tune_folds_N': sp['tune_folds_N'], 'per_lang': per, 'lang_label_L1_L2_agreement': {p: f'{a}/{b}' for p, (a, b) in agree.items()},
            'template': TEMPLATE, 'dataset': 'bigcode/humanevalpack HumanEvalFix rev 9a41762f73a8cb23bb5811b73d5aab164efcf378, MIT', 'parquet_sha256': PARQ}
    print(json.dumps(meta, ensure_ascii=False))
if __name__ == '__main__': main()
