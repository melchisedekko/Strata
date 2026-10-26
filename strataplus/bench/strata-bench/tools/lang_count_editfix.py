#!/usr/bin/env python3
"""proxy CPU, non AMD. Conteggio per linguaggio del dominio 'edit-fix' (HumanEvalFix, bigcode/humanevalpack @9a41762f).
Lingua SOLO dal prefisso di task_id '<Lang>/<N>' (colonna task_id dei parquet), controllata contro la cartella del config.
Nessun output del modello, nessuna traccia. Uso: lang_count_editfix.py DIR OUT_PREFIX"""
import sys, json, re, hashlib, time, collections, os
import pyarrow.parquet as pq
d, outp = sys.argv[1:3]
cfg = {'js': 'JavaScript', 'java': 'Java', 'go': 'Go', 'cpp': 'CPP', 'rust': 'Rust'}
per = {}; sets = {}
for c, pref in cfg.items():
    f = os.path.join(d, c, 'test-00000-of-00001.parquet')
    ids = pq.read_table(f, columns=['task_id']).column('task_id').to_pylist()
    ns = []; bad = 0
    for i in ids:
        m = re.fullmatch(r'([^/]+)/(\d+)', i)
        if not m or m.group(1) != pref: bad += 1; continue
        ns.append(int(m.group(2)))
    sets[c] = set(ns)
    per[c] = {'id_prefix': pref, 'items': len(ids), 'distinct_N': len(set(ns)), 'id_prefix_mismatch_or_malformed': bad,
              'N_min': min(ns) if ns else None, 'N_max': max(ns) if ns else None,
              'parquet_sha256': hashlib.sha256(open(f, 'rb').read()).hexdigest()}
common = sorted(set.intersection(*sets.values()))
res = {'label': 'proxy CPU, non AMD', 'created': time.strftime('%F %T %Z'), 'domain': 'edit-fix',
       'note': "dominio separato da edit/edit_np, mai sommato; split tune/holdout a cura di Policy (non qui)",
       'dataset': 'bigcode/humanevalpack', 'revision': '9a41762f73a8cb23bb5811b73d5aab164efcf378', 'license': 'MIT (card @ revisione)',
       'split_hf': 'test', 'label_source': "prefisso di task_id '<Lang>/<N>' (metadati del dataset), coerente con la cartella del config",
       'python_excluded': True, 'per_language': per, 'total_items': sum(v['items'] for v in per.values()),
       'N_in_all_5_count': len(common), 'N_in_all_5': common}
json.dump(res, open(outp + '.json', 'w'), indent=1)
L = ["# LANG_COUNT edit-fix — HumanEvalFix (bigcode/humanevalpack @9a41762f), proxy CPU, non AMD", "",
     f"Creato il {res['created']}.",
     "- Lingua presa solo dal prefisso `task_id` `<Lang>/<N>`, cioè dai metadati del dataset.",
     "- Nessuna traccia, nessun output del modello.",
     "- Dominio 'edit-fix', separato da edit/edit_np e **mai sommato**.",
     "- Lo split tune/holdout lo fa Policy.",
     "- Licenza MIT (card alla revisione 9a41762f73a8cb23bb5811b73d5aab164efcf378). Python escluso (non scaricato).", "",
     "| config | prefisso ID | item | N distinti | N min–max | ID anomali | sha256 parquet |", "|---|---|---|---|---|---|---|"]
for c, v in per.items():
    L.append(f"| {c} | {v['id_prefix']} | {v['items']} | {v['distinct_N']} | {v['N_min']}–{v['N_max']} | {v['id_prefix_mismatch_or_malformed']} | {v['parquet_sha256']} |")
L += ["", f"Totale item (5 linguaggi): {res['total_items']}.", "",
      f"**N presenti in tutti e 5 i linguaggi:** {len(common)}.",
      "Elenco completo nel .json (`N_in_all_5`). Compresso: " + (f"{common[0]}–{common[-1]} (contigui)" if common and common == list(range(common[0], common[-1] + 1)) else ", ".join(map(str, common))), ""]
open(outp + '.md', 'w').write("\n".join(L))
print(json.dumps({k: v for k, v in res.items() if k != 'N_in_all_5'})[:900])
