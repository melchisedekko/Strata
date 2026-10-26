#!/usr/bin/env python3
"""proxy CPU, non AMD. Metriche SOLO tune da traces/v1.1/*.jsonl (i file holdout_* NON vengono aperti).
live: AL = media su round di verifica di (accepted+1) per dominio.
tf (teacher-forced, verify T=1): AL_tf_Dmax7 = media su posizioni di (acc.mtp+1), acc.mtp = lcp(draft MTP Dmax=7, output) (<=7)."""
import glob, json, os, sys, collections
D = '/workspace/strata-plus/traces/v1.1'
out = {'label': 'proxy CPU, non AMD', 'source_dir': D, 'holdout_opened': False, 'runs': {}}
for f in sorted(glob.glob(f'{D}/*.jsonl')):
    b = os.path.basename(f)
    if b.startswith('holdout'): continue
    run = b[:-6]; agg = collections.defaultdict(lambda: [0, 0]); kind = None; nreq = 0; neq = 0; nend = 0
    for l in open(f):
        j = json.loads(l)
        if j['type'] == 'request': kind = j['data_kind']; nreq += 1; neq += bool(j['greedy_equal_ref'])
        elif j['type'] == 'request_end': nend += 1
        elif j['type'] == 'round':
            if kind == 'teacher_forced':
                a = j['acc']['mtp']
                if a is None: continue
                v = a + 1
            else:
                if j['source'] == 'none' and not j.get('proposal'): pass
                v = j['accepted'] + 1
            for k in (j['domain'], 'ALL'): agg[k][0] += v; agg[k][1] += 1
    out['runs'][run] = {'data_kind': kind, 'requests': nreq, 'request_end_rows': nend, 'greedy_equal_ref': neq,
                        'metric': 'AL_tf_Dmax7 = mean(acc_mtp+1) per posizione' if kind == 'teacher_forced' else 'AL = mean(accepted+1) per round di verifica',
                        'AL': {k: {'value': round(s / n, 4), 'n': n} for k, (s, n) in sorted(agg.items())}}
json.dump(out, open(sys.argv[1], 'w'), indent=1); print(json.dumps(out, indent=1))
