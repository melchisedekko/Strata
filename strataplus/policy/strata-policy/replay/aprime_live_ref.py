#!/usr/bin/env python3
"""proxy CPU, non AMD, llama.cpp non Strata. Riferimento del replay di Strata Policy per la soglia (i) di Strata Bench
(runs/live_combo_aprime_holdout_v3.md sez. 5 (i)): AL del braccio (a') (--live-src aprime = Strata --spec 8 --mtp-max-t 4,
tracer v14 con --dmax 7 --spec-draft-n-max 3) simulato sulla traccia teacher-forced holdout_tf_d7.jsonl.
Run file pre-registrato: replay/run_aprime_live_ref.json (sola lettura; lo sha256 si passa come argomento e si verifica).
L'arbitro NON e' reimplementato: si importa proxy/strata_arbiter_v1.py di Strata Bench (port 1:1 di strata_arbiter_v1.hpp).
Qui c'e' solo il "giro" del tracer v14 in modo live (llama_spec_trace_v14.cpp L320-455, L482), con accettazione ricostruita
come lcp(draft, y[pos:]) sull'output greedy y del TF e candidati MTP = primi min(3, token rimasti) dei 7 del TF (cap 3 per troncamento).
AL per round = min(accepted+1, committed) (aprime_post.py L43), per dominio somma/somma su TUTTI i round verify (sumsum_all,
il campo che aprime_toks_ab.py decide legge, L74).
Uso: aprime_live_ref.py RUN_FILE RUN_FILE_SHA256
Il tag del dominio edit si legge da STRATAPLUS_EDIT_TAG o da ${STRATAPLUS_PRIVATE_ENV:-/workspace/lic_rm/edit_dataset.env};
il suo valore non viene mai scritto nel contenuto dei file (solo nei nomi)."""
import json, sys, os, hashlib, collections, importlib.util, time
LABEL = 'proxy CPU, non AMD, llama.cpp non Strata; replay TF (holdout_tf_d7, cap 3 per troncamento), non una misura live'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
RF, RFS = sys.argv[1], sys.argv[2]
if sha(RF) != RFS: raise SystemExit('run file: sha256 diverso dal pre-registrato')
RUN = json.load(open(RF))
for k, v in RUN['inputs'].items():
    if sha(v['path']) != v['sha256']: raise SystemExit('input %s: sha256 diverso dal run file' % k)
P = RUN['params']
def edit_tag():
    t = os.environ.get('STRATAPLUS_EDIT_TAG')
    if t: return t
    pe = os.environ.get('STRATAPLUS_PRIVATE_ENV', '/workspace/lic_rm/edit_dataset.env')
    for l in open(pe):
        if l.startswith('STRATAPLUS_EDIT_TAG='): return l.split('=', 1)[1].strip()
    raise SystemExit('STRATAPLUS_EDIT_TAG non impostato')
ET = edit_tag()
spf = importlib.util.spec_from_file_location('arb', RUN['inputs']['arbiter_py']['path']); arb = importlib.util.module_from_spec(spf); spf.loader.exec_module(arb)
S, S_MTP, MINP, CAP, NPRED, NCTX, EOG = P['S'], P['S_mtp'], P['spec_min_p'], P['mtp_cap'], P['n_predict'], P['n_ctx'], set(P['eog_ids_in_y'])
# --- traccia
req, rounds = {}, collections.defaultdict(dict)
for l in open(RUN['inputs']['trace_tf_d7']['path']):
    j = json.loads(l)
    if j['type'] == 'request': req[j['req_id']] = j
    elif j['type'] == 'round': rounds[j['req_id']][j['pos']] = j
order = [k for k in req]   # ordine del file (= holdout_90.jsonl); lo stato si resetta per prompt, l'ordine non cambia nulla
def is_eog(t): return t in EOG
def lcp(d, y, p):
    a = 0
    while a < len(d) and p + a < len(y) and d[a] == y[p + a]: a += 1
    return a
per = {}; agg = collections.defaultdict(lambda: collections.Counter()); Thist = collections.defaultdict(collections.Counter)
for k in order:
    q = req[k]; y = q['output_ids']; dom = q['domain']; R = rounds[k]
    assert sorted(R) == list(range(len(y))), k
    A = arb.Arbiter(S)                       # reset per prompt: tracer v14 L199 (s = kShape di default, margin 0.03)
    p = 0; r = 0; n_predict = 0; c = collections.Counter(); sv = [0, 0, 0, 0]
    while True:
        t = R[p]; mt = t['cand']['mtp']['tokens']; mp = t['cand']['mtp']['probs']
        lt = t['cand']['lookup']['tokens']; lmatch = t['cand']['lookup']['match']; lk = len(lt)
        n_past = q['prompt_tokens'] - 1 + p   # posizione di id_last prima del round (prefill di inp[0..n-2], poi +committed)
        n_draft_max = max(min(NCTX - n_past - 2, NPRED - n_predict - 1), 0)   # v14 L330-333
        cap = min(n_draft_max, CAP)                                             # v14 L335 (live)
        mtp_cand, mtp_pg = mt[:cap], mp[:cap]                                   # LIMITE: troncamento dei 7 token TF
        fw = r == 0
        k_used = min(lk, S - 1)                                                 # v14 L358
        if fw: T, lookup, gate = 1, False, False
        else:
            d = arb.decide(A, S, S_MTP, MINP, mtp_pg, k_used, lmatch, lt[0] if lk > 0 else -1, mtp_cand[0] if mtp_cand else -2, 1 + n_draft_max)
            T, lookup, gate = d['T'], d['lookup'], d['gate']
        nd = T - 1
        draft = lt[:min(nd, lk)] if lookup else mtp_cand[:min(nd, len(mtp_cand))]   # v14 L363-364
        acc = lcp(draft, y, p)                                                 # sample_and_accept_n greedy (L408) = lcp con y
        ids = y[p:p + acc + 1]
        n_eos = len(ids)
        for i, x in enumerate(ids):
            if is_eog(x): n_eos = i + 1; break
        if len(ids) < acc + 1 and n_eos == len(ids): raise SystemExit('%s pos %d: draft oltre la fine di y senza EOG' % (k, p))
        acc_c = min(acc, n_eos)                                                 # v13/v14 L444 (ids.size()-1 = acc)
        committed = n_eos
        v = min(acc_c + 1, committed)                                           # aprime_post.py L43
        sv[0] += v; sv[1] += 1
        if not fw: sv[2] += v; sv[3] += 1
        src = 'first_window' if fw else ('lookup' if lookup else 'mtp')
        c['rounds'] += 1; c['src_' + src] += 1; c['tok_' + src] += v; c['drafted_' + src] += len(draft); c['acc_' + src] += acc_c
        if not fw: c['gate_true' if gate else 'gate_false'] += 1
        if gate and not lookup: c['gate_true_mtp_chosen'] += 1
        if not fw and n_draft_max < CAP: c['rounds_cap_lt3_tail'] += 1
        if not fw and lookup and k_used >= 1 and min(nd, lk) < nd: c['lookup_draft_shorter_than_T'] += 1
        Thist[dom][(src, T)] += 1
        r += 1
        if not fw: A.observe(lookup, T, acc_c, lmatch)                         # v14 L455 (solo !first_window)
        p += n_eos                                                              # token aggiunti all'output (fino al primo EOG incluso)
        n_predict += len(ids)
        has_eos = any(is_eog(x) for x in ids)                                     # v14 L477 (output si ferma al primo EOG)
        if has_eos or n_predict >= NPRED: break                                  # v14 L482
        if p >= len(y): raise SystemExit('%s: fine di y senza EOG ne n_predict' % k)
    if p != len(y): raise SystemExit('%s: committed %d != len(y) %d' % (k, p, len(y)))
    per[k] = {'domain': dom, 'rounds': sv[1], 'tokens': sv[0], 'AL': sv[0] / sv[1], 'rounds_excl_fw': sv[3], 'tokens_excl_fw': sv[2], 'counters': dict(c)}
    a = agg[dom]; a['prompts'] += 1; a['sum_v'] += sv[0]; a['n'] += sv[1]; a['sum_v_xfw'] += sv[2]; a['n_xfw'] += sv[3]; a.update(c)
doms = sorted(agg)
AL = {d: round(agg[d]['sum_v'] / agg[d]['n'], 6) for d in doms}
mpp = {d: round(sum(x['AL'] for x in per.values() if x['domain'] == d) / agg[d]['prompts'], 6) for d in doms}
xfw = {d: round(agg[d]['sum_v_xfw'] / max(1, agg[d]['n_xfw']), 6) for d in doms}
O = RUN['outputs']; od = O['dir']; os.makedirs(od, exist_ok=True); os.makedirs(O['local_dir'], exist_ok=True)
fref = os.path.join(od, O['reference'].replace('<ET>', ET)); fcov = os.path.join(od, O['coverage'].replace('<ET>', ET))
fper = os.path.join(O['local_dir'], O['per_prompt_local'].replace('<ET>', ET))
meta = {'label': LABEL, 'created': time.strftime('%Y-%m-%d %H:%M:%S CET (UTC+1)'), 'run_file': RF, 'run_file_sha256': RFS,
        'script': os.path.abspath(__file__), 'script_sha256': sha(os.path.abspath(__file__)), 'definition': RUN['AL_definition']['text']}
ref = dict(meta, AL=AL, AL_mean_per_prompt_info=mpp, AL_sumsum_excl_first_window_info=xfw,
           rounds={d: agg[d]['n'] for d in doms}, prompts={d: agg[d]['prompts'] for d in doms},
           note='chiave letta da aprime_toks_ab.py decide: AL (domini code/edit nel criterio; chat solo riportata in al_dev_vs_replay)')
json.dump(ref, open(fref, 'w'), indent=1)
cov = dict(meta, domains={d: dict(agg[d], AL_sumsum=AL[d], AL_mean_per_prompt=mpp[d], AL_sumsum_excl_first_window=xfw[d],
                                  T_hist={'%s:T%d' % kk: v for kk, v in sorted(Thist[d].items())}) for d in doms})
json.dump(cov, open(fcov, 'w'), indent=1)
json.dump(dict(meta, per_prompt=per), open(fper, 'w'), indent=1)
open(fref + '.sha256', 'w').write('%s  %s\n' % (sha(fref), os.path.basename(fref)))
print(json.dumps({'AL': {d: AL[d] for d in doms if d != 'edit'}, 'rounds': {d: agg[d]['n'] for d in doms}, 'prompts': {d: agg[d]['prompts'] for d in doms}}))
