# Annotazione licenze + verifica disgiunzione ID check_v12 vs v1.1 (tune/holdout/diag/agent/mtbench2) e p4. Nessuna metrica.
import json,glob,sys,hashlib,os
def _private(key):
    """Valore SOLO LOCALE (mai pubblicato) del dataset di edit con licenza non pubblicabile (etichetta pubblica: edit_np).
    Ordine: variabile d'ambiente `key`; altrimenti il file locale STRATAPLUS_PRIVATE_ENV
    (default /workspace/lic_rm/edit_dataset.env, righe KEY=VALORE). Se manca: errore esplicito."""
    v = os.environ.get(key, "").strip()
    path = os.environ.get("STRATAPLUS_PRIVATE_ENV", "/workspace/lic_rm/edit_dataset.env")
    if not v and os.path.isfile(path):
        for line in open(path):
            k, _, x = line.strip().partition("=")
            if k == key:
                v = x.strip()
    if not v:
        sys.exit(f"ERRORE: {key} non impostata (ne' in ambiente ne' in {path}). "
                 "Impostala o crea il file locale: vedi /workspace/lic_rm/README_edit_dataset.md")
    return v
EDIT_TAG = _private("STRATAPLUS_EDIT_TAG")  # etichetta locale del dataset di edit con licenza non pubblicabile
OUT=sys.argv[1]
LIC={'humaneval':('code','MIT','HF openai/openai_humaneval @ 7dce6050a7d6d172f3cc5c32aa97f52fa1a2e544'),
     'mt-bench':('chat','Apache-2.0 (repo FastChat)','lm-sys/FastChat @ 587d5cfa1609a43d192cedb8441cac3c17db105d fastchat/llm_judge/data/mt_bench/question.jsonl'),
     EDIT_TAG:('edit','MIT','HF %s @ %s' % (_private('STRATAPLUS_EDIT_DATASET'), _private('STRATAPLUS_EDIT_DATASET_REV')))}
rows=[json.loads(l) for l in open('datasets/check_v12.jsonl')]
other={}
for f in sorted(glob.glob('/workspace/strata-plus/traces/v1.1/*.jsonl')):
  for l in open(f):
    j=json.loads(l)
    if j.get('type')=='request': other.setdefault(j['req_id'],set()).add(f.split('/')[-1])
for l in open('datasets/p4_prompts.jsonl'):
  j=json.loads(l); other.setdefault(j.get('id'),set()).add('p4_prompts.jsonl')
req=[];ov=[]
for r in rows:
  d,lic,up=LIC[r['source']]
  assert d==r['category']
  req.append({'req_id':r['id'],'domain':d,'source':r['source'],'license':lic,'upstream':up,'prompt_sha256':hashlib.sha256(r['prompt'].encode()).hexdigest()})
  if r['id'] in other: ov.append([r['id'],sorted(other[r['id']])])
cnt={}
for q in req: cnt[q['domain']]=cnt.get(q['domain'],0)+1
json.dump({'label':'proxy CPU, non AMD','split':'check_v12','license_source':'/workspace/strata-plus/traces/DATASETS.md righe 9-11',
 'counts':cnt,'n_v11_and_p4_ids_checked':len(other),'overlap_with_v11_or_p4':ov,'disjoint':not ov,'requests':req},open(OUT,'w'),indent=1)
print(cnt,'checked',len(other),'overlap',ov)
