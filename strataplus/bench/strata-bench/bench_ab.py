#!/usr/bin/env python3
"""Harness A/B (ABBA) per l'eseguibile `strata` (modalità generate; nessun sottocomando, `add_executable(strata src/program/generate.cpp)` CMakeLists.txt:759) — Strata+ / Strata Bench.

Esegue B + config A_i in ordine ABBA su sottoinsiemi fissi, registra comando/commit/driver/env, output grezzo JSONL,
tok/s, speedup appaiato, media/std/IC95, accettati per round per dominio e uguaglianza greedy.
Parsa il formato REALE di Strata @7dd5cf18 (src/program/generate.cpp):
  16727  "speculation              N rounds of T, drafts accepted a of b (r), x tokens per round"
  16733  "window sizes             T1:n T2:n ...  (min draft probability p)"
  16739  "suffix drafts            N windows, drafts accepted a of b"
  16742  "lookup chain             N windows, chained drafts accepted a of b"
  16758  "accepted per round       0:n 1:n ..."
  16867  "prompt  : ids" / "output  : ids"
  16874  "decode                   N tokens in X ms  ->  Y tok/s"
  STRATA_SPEC_TRACE (16398-16407): "T a sfx ms p1 p2 ..." per round.
Non eseguito su GPU in questa box (nessuna GPU): `--self-test` verifica solo il parser su testo sintetico.
"""
import argparse, datetime, hashlib, json, math, os, platform, random, re, shlex, statistics as st, subprocess, sys

CONFIGS = {   # PROTOCOL.md §2
    'B':  {'args': ['--spec', '1'], 'env': {}},
    'A1': {'args': ['--spec', '4', '--spec-min-p', '0.5'], 'env': {}},
    'A2': {'args': ['--spec', '4', '--spec-min-p', '0.5', '--lookup-chain', '4'], 'env': {}},
    'A3': {'args': ['--spec', '4', '--spec-min-p', '0.5'], 'env': {'STRATA_SPEC_COST': '1'}},
    'A4': {'args': ['--spec', '4', '--spec-min-p', '0.5', '--suffix-draft', '0'], 'env': {}},
    # A5 (lookup-only) va misurato via `strata --serve` senza MTP: non coperto da questo harness (PROTOCOL.md §2)
}

RX = {
    'spec': re.compile(r'^speculation\s+(\d+) rounds of (\d+), drafts accepted (\d+) of (\d+) \(([\d.]+)\), ([\d.]+) tokens per round', re.M),
    'win': re.compile(r'^window sizes\s+(.*?)\s+\(min draft probability', re.M),
    'sfx': re.compile(r'^suffix drafts\s+(\d+) windows, drafts accepted (\d+) of (\d+)', re.M),
    'chain': re.compile(r'^lookup chain\s+(\d+) windows, chained drafts accepted (\d+) of (\d+)', re.M),
    'acc': re.compile(r'^accepted per round\s+(.*)$', re.M),
    'out': re.compile(r'^output  :(.*)$', re.M),
    'dec': re.compile(r'^decode\s+(\d+) tokens in ([\d.]+) ms\s+->\s+([\d.]+) tok/s', re.M),
}

def parse(stdout):
    m = {}
    if (x := RX['dec'].search(stdout)): m.update(decoded=int(x[1]), decode_ms=float(x[2]), tok_s=float(x[3]))
    if (x := RX['spec'].search(stdout)):
        m.update(rounds=int(x[1]), spec_T=int(x[2]), drafts_ok=int(x[3]), drafts_total=int(x[4]), tokens_per_round=float(x[6]))
    if (x := RX['win'].search(stdout)): m['window_hist'] = {k: int(v) for k, v in (t.split(':') for t in x[1].split())}
    if (x := RX['sfx'].search(stdout)): m.update(sfx_windows=int(x[1]), sfx_ok=int(x[2]), sfx_drafts=int(x[3]))
    if (x := RX['chain'].search(stdout)): m.update(chain_windows=int(x[1]), chain_ok=int(x[2]), chain_drafts=int(x[3]))
    if (x := RX['acc'].search(stdout)): m['accepted_hist'] = {int(k): int(v) for k, v in (t.split(':') for t in x[1].split())}
    if (x := RX['out'].search(stdout)): m['output_ids'] = [int(t) for t in x[1].split()]
    return m

def parse_spec_trace(path):
    rows = []
    for l in open(path):
        f = l.split()
        if len(f) >= 4: rows.append({'T': int(f[0]), 'a': int(f[1]), 'sfx': int(f[2]), 'ms': float(f[3]), 'p': [float(v) for v in f[4:]]})
    return rows

def sh(cmd):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as e: return f'ERR {e}'

def meta(a):
    env = {k: v for k, v in os.environ.items() if k.startswith(('STRATA_', 'HIP_', 'ROCR_', 'HSA_', 'CUDA_', 'GPU_'))}
    return {'time': datetime.datetime.now().astimezone().isoformat(), 'argv': sys.argv, 'strata': a.strata,
            'strata_commit': sh(f'git -C {shlex.quote(a.repo)} rev-parse HEAD'), 'strata_dirty': sh(f'git -C {shlex.quote(a.repo)} status --porcelain'),
            'strata_version': sh(f'{shlex.quote(a.strata)} --version'), 'rocm_smi': sh('rocm-smi --showdriverversion --showproductname'),
            'hipconfig': sh('hipconfig --version'), 'nvidia_smi': sh('nvidia-smi --query-gpu=name,driver_version,clocks.sm --format=csv'),
            'kernel': platform.release(), 'cpu': sh("lscpu | grep 'Model name'"), 'env': env}

def ci95_t(xs):
    n = len(xs)
    if n < 2: return [None, None]
    tq = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57, 8: 2.36, 10: 2.26, 15: 2.14, 20: 2.09, 30: 2.05}
    t = tq.get(n, tq[min(tq, key=lambda k: abs(k - n))] if n < 30 else 1.96)
    h = t * st.stdev(xs) / math.sqrt(n); m = st.mean(xs)
    return [m - h, m + h]

def summarize(rows, base='B'):
    out = {}
    key = {(r['config'], r['rep'], r['id']): r for r in rows}
    for c in sorted({r['config'] for r in rows}):
        for dom in sorted({r['domain'] for r in rows}) + ['all']:
            rs = [r for r in rows if r['config'] == c and (dom == 'all' or r['domain'] == dom)]
            sp, eq, n = [], 0, 0
            for r in rs:
                b = key.get((base, r['rep'], r['id']))
                if b and 'tok_s' in b['m'] and 'tok_s' in r['m']:
                    sp.append(r['m']['tok_s'] / b['m']['tok_s'])
                    n += 1; eq += r['m'].get('output_ids') == b['m'].get('output_ids')
            rounds = sum(r['m'].get('rounds', 0) for r in rs); ok = sum(r['m'].get('drafts_ok', 0) for r in rs)
            out[f'{c}/{dom}'] = {'n': len(rs), 'tok_s_mean': st.mean([r['m']['tok_s'] for r in rs if 'tok_s' in r['m']] or [0]),
                                 'speedup_mean': st.mean(sp) if sp else None, 'speedup_std': st.stdev(sp) if len(sp) > 1 else None,
                                 'speedup_ci95': ci95_t(sp), 'AL': (ok + rounds) / rounds if rounds else None,
                                 'greedy_equal': f'{eq}/{n}'}
    return out

def self_test():
    s = ("prompt  : 1 2 3\noutput  : 10 11 12 13\n"
         "speculation              5 rounds of 4, drafts accepted 7 of 15 (0.467), 2.40 tokens per round\n"
         "window sizes             T1:1 T2:0 T3:1 T4:3  (min draft probability 0.50)\n"
         "suffix drafts            2 windows, drafts accepted 3 of 6\n"
         "accepted per round       0:1 1:1 2:1 3:2\n"
         "decode                   12 tokens in 300.0 ms  ->  40.00 tok/s\n")
    m = parse(s)
    assert m['rounds'] == 5 and m['drafts_ok'] == 7 and m['tok_s'] == 40.0 and m['output_ids'] == [10, 11, 12, 13]
    assert m['window_hist'] == {'T1': 1, 'T2': 0, 'T3': 1, 'T4': 3} and m['accepted_hist'][3] == 2 and m['sfx_ok'] == 3
    print('self-test OK (testo SINTETICO nel formato di generate.cpp, non un run reale):', json.dumps(m))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--strata', default='build/strata'); ap.add_argument('--repo', default='/workspace/strata-src')
    ap.add_argument('--model-args', default='', help='argomenti del modello/pack passati invariati (es. "--pack … --mtp …")')
    ap.add_argument('--prompts', help='JSONL con id, category, tokens (lista id) — tokenizzato col tokenizer del modello')
    ap.add_argument('--configs', default='B,A1,A2,A3,A4'); ap.add_argument('--reps', type=int, default=3)
    ap.add_argument('--max-new', type=int, default=256); ap.add_argument('--out', default='runs')
    ap.add_argument('--spec-trace', action='store_true', help='STRATA_SPEC_TRACE per round'); ap.add_argument('--plus-trace', action='store_true', help='STRATA_PLUS_TRACE (patch locale)')
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test: return self_test()
    prompts = [json.loads(l) for l in open(a.prompts)]
    cfgs = a.configs.split(',')
    assert cfgs[0] == 'B', 'la prima config deve essere la baseline B'
    od = os.path.join(a.out, datetime.datetime.now().strftime('%Y%m%d-%H%M%S')); os.makedirs(od, exist_ok=True)
    json.dump(meta(a), open(f'{od}/meta.json', 'w'), indent=1)
    raw = open(f'{od}/raw.jsonl', 'a'); rows = []
    for rep in range(a.reps):
        order = cfgs if rep % 2 == 0 else cfgs[::-1]            # ABBA: B A1..Ak | Ak..A1 B | …
        for c in order:
            for p in prompts:
                tf = f'{od}/tok_{hashlib.sha1(p["id"].encode()).hexdigest()[:10]}.txt'
                open(tf, 'w').write(','.join(map(str, p['tokens'])))
                cmd = [a.strata, *shlex.split(a.model_args), '--tokens-file', tf, '--max-new', str(a.max_new), '--greedy', *CONFIGS[c]['args']]
                env = dict(os.environ, **CONFIGS[c]['env'])
                tag = f'{c}_r{rep}_{p["id"].replace("/", "_")}'
                if a.spec_trace: env['STRATA_SPEC_TRACE'] = f'{od}/spec_{tag}.txt'
                if a.plus_trace: env['STRATA_PLUS_TRACE'] = f'{od}/plus_{tag}.jsonl'
                rec = {'config': c, 'rep': rep, 'id': p['id'], 'domain': p.get('category'), 'cmd': shlex.join(cmd), 'env_delta': CONFIGS[c]['env']}
                if a.dry_run:
                    print(rec['cmd'], CONFIGS[c]['env']); continue
                t = datetime.datetime.now().astimezone().isoformat()
                r = subprocess.run(cmd, env=env, capture_output=True, text=True)
                rec.update(start=t, rc=r.returncode, stdout=r.stdout, stderr=r.stderr[-20000:], m=parse(r.stdout))
                if a.spec_trace and os.path.exists(env['STRATA_SPEC_TRACE']): rec['spec_trace'] = parse_spec_trace(env['STRATA_SPEC_TRACE'])
                raw.write(json.dumps(rec) + '\n'); raw.flush(); rows.append(rec)
    if rows:
        s = summarize(rows); json.dump(s, open(f'{od}/summary.json', 'w'), indent=1); print(json.dumps(s, indent=1))

if __name__ == '__main__':
    main()
