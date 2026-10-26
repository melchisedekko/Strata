#!/usr/bin/env python3
"""proxy CPU, modello denso, non AMD. Analisi ginocchio T=8 -> traces/p4_knee_T8.json (+ .sha256)."""
import numpy as np, json, hashlib, random, re, statistics as st, time, os, collections
TR = '/workspace/strata-plus/traces'; RAW = f'{TR}/raw/v11/knee'
import glob
CFG = {f'{m}_{c}': f for m in ('q4km', 'q8') for c, f in (('main', '-t 6 -ub 512 (LLAMAFILE ON, blocchi b1,b4,b5,b8)'), ('llamafile_off', '-t 6 -ub 512, build -DGGML_LLAMAFILE=OFF (blocchi b2,b3,b6,b7)'), ('ctrl_ub256', '-t 6 -ub 256'), ('ctrl_t8', '-t 8 -ub 512'))}
J = '/tmp/knee_test.json'
if os.path.exists(J): raise SystemExit('REFUSED: ' + J + ' esiste gia\' (immutabile)')
TS = [6, 7, 8, 9, 10]; NB = 4000; RNG = np.random.default_rng(20261025)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def q(v, p):
    v = sorted(v); i = (len(v) - 1) * p; lo = int(i); hi = min(lo + 1, len(v) - 1); return v[lo] + (v[hi] - v[lo]) * (i - lo)
def summ(v):
    a = np.asarray(v); meds = list(np.median(a[RNG.integers(0, len(a), size=(NB, len(a)))], axis=1))
    return {'median': round(st.median(v), 4), 'q25': round(q(v, .25), 4), 'q75': round(q(v, .75), 4), 'iqr': round(q(v, .75) - q(v, .25), 4),
            'ci95_median_bootstrap': [round(q(meds, .025), 4), round(q(meds, .975), 4)], 'n': len(v)}
def cpu_block(p):
    b = os.path.basename(p)[:-6]; logs = sorted(glob.glob(f'{RAW}/cpu_{b}_a*.log'))
    if logs:  # rifatto con run_knee_redo.sh: monitor /proc a 2 s (carico estraneo in core, esclusi llama_spec_trace)
        v = [float(l.split()[1]) for l in open(logs[-1]) if len(l.split()) > 1]
        return {'block': b, 'method': 'proc_delta_2s', 'log': logs[-1], 'intervals': len(v), 'foreign_cores_max': round(max(v), 3) if v else None,
                'foreign_cores_median': round(st.median(v), 3) if v else None, 'intervals_ge_0.5': sum(x >= .5 for x in v), 'valid': all(x < .5 for x in v)}
    c = contamination(b[5:], exact=True); c.update(block=b, method='ps_lifetime_pcpu_5s', valid=c['snapshots_with_foreign_proc_gt20pct'] == 0); return c
def contamination(name, exact=False):
    snaps, bad, cur, hit = 0, 0, False, False
    for l in open(f'{RAW}/ps.log'):
        if l.startswith('== '):
            if cur and hit: bad += 1
            cur = re.search((rf'DURING knee_{name}$' if exact else rf'DURING knee_{name}(_b\d)?$'), l.strip()) is not None; hit = False; snaps += cur; continue
        if cur:
            f = l.split()
            if len(f) > 2 and re.match(r'^[\d.]+$', f[1]) and float(f[1]) > 20 and 'llama_spec_trace' not in l and 'ps -eo' not in l: hit = True
    if cur and hit: bad += 1
    return {'snapshots_5s': snaps, 'snapshots_with_foreign_proc_gt20pct': bad}
cmds = {l.split('--tag ')[1].split()[0]: l.strip() for l in open(f'{RAW}/cmds.txt')}
out = {'schema_version': 'p4knee.v2', 'label': 'proxy CPU, modello denso, non AMD', 'created': time.strftime('%F %T %Z'),
       'models': {'q4km': 'models/qwen35-2b-mtp-q4_k_m.gguf', 'q8': 'models/qwen35-2b-mtp-q8_0.gguf'}, 'd': 0,
       'design': 'verify-only, T in {1,6,7,8,9,10}; 6 prompt (datasets/p4_prompts.jsonl); ON/OFF interleaved ABBA a blocchi di 25 rep (on b1,b4,b5,b8 / off b2,b3,b6,b7) = 100 rep per braccio; controlli 100 rep; per ogni rep l\'ordine dei T e\' ruotato di rep//2 e invertito sulle rep dispari; 3 giri di warm-up',
       'unit': 'campione = (prompt, rep): s(T) = ms_verify(T) / ms_verify(T=1) della stessa rep; statistiche su 600 campioni per punto (6 prompt x 100 rep); CI = bootstrap percentile della mediana, 4000 ricampionamenti, seed 20261025',
       'binary_sha256': {b: sha(f'/workspace/strata-bench/proxy/llama_spec_trace.{b}.bin') for b in ('v11knee', 'v11knee.nollamafile')}, 'configs': {},
       'invalid_blocks': json.load(open(f'{RAW}/invalid/invalid.json')) if os.path.exists(f'{RAW}/invalid/invalid.json') else [],
       'invalid_note': 'blocchi contaminati da processi di altri agenti (apt ROCm, compilazioni, git fetch, script python): raw spostati in raw/v11/knee/invalid/, esclusi dalle statistiche e rifatti con run_knee_redo.sh (pre-check: carico estraneo <0.5 core per 30 s da delta /proc; blocco INVALID se un intervallo di 2 s ha carico estraneo >=0.5 core). I blocchi rifatti seguono temporalmente gli altri: l\'interleaving ABBA originale e\' parzialmente perso per q4km (b4,b5,b7,b8 rifatti dopo b1,b2,b3,b6).'}
for name, flags in CFG.items():
    ps_ = [f'{RAW}/knee_{name}.jsonl'] if os.path.exists(f'{RAW}/knee_{name}.jsonl') else sorted(glob.glob(f'{RAW}/knee_{name}_b*.jsonl'))
    if not ps_: continue
    ms = collections.defaultdict(dict)
    for p in ps_:
        for l in open(p):
            j = json.loads(l)
            if j.get('what') == 'verify': ms[(p, j['req_id'], j['rep'])][j['T']] = j['ms']
    units = [u for u in ms.values() if all(t in u for t in [1] + TS)]
    s = {T: [u[T] / u[1] for u in units] for T in TS}
    d76 = [a - b for a, b in zip(s[7], s[6])]; d87 = [a - b for a, b in zip(s[8], s[7])]; d98 = [a - b for a, b in zip(s[9], s[8])]
    out['configs'][name] = {'flags': flags, 'command': [cmds.get(os.path.basename(p)[:-6]) for p in ps_], 'raw': ps_, 'raw_sha256': [sha(p) for p in ps_],
        '_s_raw': s,
        'ms_verify_T1': summ([u[1] for u in units]), 'ms_verify': {str(T): summ([u[T] for u in units]) for T in TS},
        's': {str(T): summ(s[T]) for T in TS},
        'inc_s7_minus_s6': summ(d76), 'inc_s8_minus_s7': summ(d87), 'inc_s9_minus_s8': summ(d98),
        'inc87_minus_inc76': summ([a - b for a, b in zip(d87, d76)]),
        'cpu_check': [cpu_block(p) for p in ps_]}
    out['configs'][name]['all_blocks_valid'] = all(c['valid'] for c in out['configs'][name]['cpu_check'])
def dmed(a, b):
    a = np.asarray(a); b = np.asarray(b)
    d = np.median(a[RNG.integers(0, len(a), size=(NB, len(a)))], axis=1) - np.median(b[RNG.integers(0, len(b), size=(NB, len(b)))], axis=1)
    return {'median_on_minus_median_off': round(float(np.median(a) - np.median(b)), 4), 'ci95_bootstrap': [round(float(np.quantile(d, .025)), 4), round(float(np.quantile(d, .975)), 4)]}
for m in ('q4km', 'q8'):
    on, off = out['configs'].get(f'{m}_main'), out['configs'].get(f'{m}_llamafile_off')
    if on and off:
        out.setdefault('on_vs_off', {})[m] = {str(T): dmed(on['_s_raw'][T], off['_s_raw'][T]) for T in TS}
for c in out['configs'].values(): c.pop('_s_raw', None)
json.dump(out, open(J, 'w'), indent=1)
open(J + '.sha256', 'w').write(f'{sha(J)}  p4_knee_T8.json\n')
print(time.strftime('%F %T %Z'), 'p4_knee_T8.json', sha(J))
for n, c in out['configs'].items():
    print(n, {T: c['s'][T]['median'] for T in c['s']}, 'inc76', c['inc_s7_minus_s6']['median'], c['inc_s7_minus_s6']['ci95_median_bootstrap'],
          'inc87', c['inc_s8_minus_s7']['median'], c['inc_s8_minus_s7']['ci95_median_bootstrap'], c['all_blocks_valid'])
