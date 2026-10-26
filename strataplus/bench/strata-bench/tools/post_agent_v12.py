#!/usr/bin/env python3
"""proxy CPU, non AMD. Dopo annotate_v11.py (ANN_SPLIT=agent_v12) su raw/agent_v12: aggiunge a header e righe request di
traces/agent_v12/*.jsonl licenza (MIT Strata), metadati di troncamento (ctx 49152, dal dataset agent_v12_c49k.jsonl), build
(binario v12 LLAMAFILE OFF, sha256) e i campi v12 raw_prompt/vmrss_kb/vmhwm_kb/n_ctx dalla riga raw. Nessuna metrica."""
import json, sys, glob, os, hashlib
V, RAW, DS, BIN = sys.argv[1:5]
ds = {json.loads(l)['id']: json.loads(l) for l in open(DS)}
bsha = hashlib.sha256(open(BIN, 'rb').read()).hexdigest()
build = {'binary': os.path.basename(BIN), 'binary_sha256': bsha, 'source': 'proxy/llama_spec_trace_v12.cpp',
         'source_sha256': hashlib.sha256(open('/workspace/strata-bench/proxy/llama_spec_trace_v12.cpp', 'rb').read()).hexdigest(),
         'ggml_libs': '/workspace/llama.cpp/build-nollamafile/bin (GGML_LLAMAFILE=OFF)'}
for f in sorted(glob.glob(f'{V}/agent_v12_*.jsonl')):
    run = os.path.basename(f)[:-6]; extra = {}
    for l in open(f'{RAW}/{run}.jsonl'):
        j = json.loads(l)
        if j['type'] in ('request', 'request_end'):
            extra.setdefault(j['req_id'], {}).update({k: j[k] for k in ('raw_prompt', 'vmrss_kb', 'vmhwm_kb', 'n_ctx') if k in j})
    out = []
    for l in open(f):
        j = json.loads(l)
        if j['type'] == 'header': j.update({'build': build, 'license': ds[next(iter(ds))]['license'], 'ctx_limit': 49152})
        if j['type'] == 'request':
            d = ds[j['req_id']]; j.update({'license': d['license'], 'truncation': d['truncation'], 'build': build, **extra.get(j['req_id'], {})})
        out.append(json.dumps(j, ensure_ascii=False))
    open(f, 'w').write('\n'.join(out) + '\n'); print(run, len(out))
