# Run file tracce H-LANG / edit-fix v1 — `runs/run_hlang_editfix_traces_v1.sh`
**proxy CPU, non AMD, llama.cpp non Strata.** Scritto il 27/10/2026 ~13:5x CET. **SCRITTO, NON LANCIATO.** Controlli fatti senza eseguire il
run: `bash -n` OK; `py_compile` OK su `tools/prepare_hlang_editfix_prompts.py` e sul blocco python di validazione. Nessun processo llama avviato.
Si lancia solo su richiesta esplicita, in una finestra annunciata, dopo le 10 build ROCm 6.4.4 e la (a′) (AMD_PROTOCOL_v5.md sez. 14).

## 1. Split di Policy: le due copie e la verifica
| copia | percorso | sha256 | esito (27/10 ~13:4x CET) |
|---|---|---|---|
| riferimento di pre-registrazione | `/workspace/lic_rm/orig_2026-10-27/workspace/strata-policy/replay/run_hlang_editfix.json` | `bbb9eb220f5a6aa5e95f15f05b85d9daf2e1684e7da86506a17cca4b8f103dde` | OK |
| copia pubblica per il fork | `/workspace/strata-policy/replay/run_hlang_editfix.json` | `dd1b8ee8a9932331d15244e220791f975c5800fe224d16778ab70d8a85661d0e` | OK |

- **Riga cambiata: 291** (chiave top-level `publication`, nota di pubblicazione). Verifica programmatica: 293/293 righe in entrambe, unica
  riga diversa = 291; unica chiave top-level diversa = `publication`; **`split` identico (True)**. Split, seed e soglie identici (conferma di
  Strata Lead 27/10 13:34 CET). Il riferimento non sta nella radice di `orig_2026-10-27/`, ma in `workspace/strata-policy/replay/` sotto di essa.
- Ricontrollo dello split: insiemi tune/holdout/riserva disgiunti, unione = N 0..163; rigenerazione da seed 20261026
  (`random.Random(seed).shuffle(sorted(range(164)))`, tune = primi 40, holdout = 40 successivi, riserva = 84) identica per tune, holdout e
  riserva; unione dei 5 fold (`tune_folds_N`, 8 N ciascuno) = tune_N. **Esito: split identico, nessun motivo di fermarsi.**
- All'avvio lo script verifica lo sha di ogni copia presente, usa lo split del **riferimento** se c'è (altrimenti quello della copia pubblica)
  e si ferma se, con entrambe presenti, gli split differiscono (`tools/prepare_hlang_editfix_prompts.py --check`). Poi rigenera i prompt dallo
  split e dai parquet e si ferma se non coincidono byte per byte con i file hashati.
- tune_N (40): 4,6,9,15,20,23,24,27,42,44,46,48,63,65,66,67,76,79,83,93,94,97,105,107,108,114,120,121,126,129,132,133,135,139,140,153,158,159,162,163
- holdout_N (40): 0,3,5,10,11,12,31,32,36,37,38,40,45,51,53,56,62,71,73,75,77,89,92,113,116,118,119,122,131,136,141,145,147,149,150,152,156,157,160,161
- Le 84 N di riserva **non si tracciano** (servirebbe un nuovo run file, regola di Policy).

## 2. Dataset e prompt
- HumanEvalFix, bigcode/humanevalpack rev `9a41762f73a8cb23bb5811b73d5aab164efcf378` (MIT), `datasets/humanevalfix_9a41762f/{js,java,go,cpp,rust}/test-00000-of-00001.parquet`
  (sha256 in `SHA256SUMS`, ricontrollati da `prepare_hlang_editfix_prompts.py`). 5 linguaggi × 40 N = 200 item per tune e 200 per holdout.
- File dei prompt (nuovi, hashati, sola lettura): `datasets/hlang_editfix_tune.jsonl` (200 righe, sha256 `101bfa2ea7c1d06fa95fd792735f87a4fcb54710e32d3931b594a799df6947f2`),
  `datasets/hlang_editfix_holdout.jsonl` (200 righe, `b207b9edd407d47cbfcf8c1d65a2db4910bd0622fa552cf1c75d6cb8650c264e`),
  metadati `datasets/hlang_editfix_prompts_meta.json` (`31414e21efeef4fd9b922965643e66ea88105db00cb71c4540e435128553634a`), generati da
  `tools/prepare_hlang_editfix_prompts.py` (`f62a22b6f9c96750eef8ca96fb98266985c1d0847ec81abdd76385ffe811f135`), eseguito con
  `nice -n 19 /tmp/venv_pa/bin/python` (pyarrow); nessun modello.
- Campi: `id` = task_id (es. `JavaScript/4`), `category` = `edit-fix` (il tracer lo scrive come `domain`), `source` = `humanevalfix`
  (diventa `dataset`), `prompt`; campi informativi ignorati dal tracer: `lang`, `N`, `split`, `fold` (solo tune). Ordine: N crescente, poi
  JS, Java, Go, CPP, Rust.
- **Template del prompt = proposta di Bench, da confermare con Policy prima del lancio** (il run file di Policy non lo fissa). È ispirato a
  HumanEvalFixTests di OctoPack (dichiarazione + soluzione con bug + test):
  `` Fix bugs in `{entry_point}`. The following {JavaScript|Java|Go|C++|Rust} code contains a bug. Reply with the full fixed code in one code block. ``
  seguito da un fence ```` ```{javascript|java|go|cpp|rust} ```` con `declaration + buggy_solution` e da `Tests:` con un fence con `test`.
  Il tracer v11 aggiunge il template chat Qwen (sorgente attuale `proxy/llama_spec_trace.cpp` L159: `<|im_start|>user\n…<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n`).
- Etichette di linguaggio: `LANG_LABEL_RULE.md` (sha256 `344a793b42fb7cfc100698177a3b5207e6686dba591064f205d2c13471da49a3`, verificato).
  L1 (primaria) = prefisso del task_id → javascript/java/go/cpp/rust; L2 (controllo causale) = prima info-string di fence nel prompt.
  Accordo L1/L2: **200/200 tune, 200/200 holdout** (per costruzione del template). Per linguaggio: 40 in ogni split.
- Lunghezza dei prompt: 365–3722 caratteri (tune), 418–2876 (holdout). Il tracer salta i prompt troppo lunghi per `-c 8192`; lo script si
  ferma se ne salta anche uno solo (`skip` nello stderr).

## 3. Tracer, flag, formato (= tune H-CA)
- Non c'è un run file H-CA in `runs/`: le tracce del tune H-CA sono `strata-plus/traces/v1.1/tf_d7_p30.jsonl` (sha256 `87efe507324b2a79…`),
  prodotte da `/workspace/strata-bench/run_v11.sh` (sha256 `831a9f2c91ea2658ac364c34a7229d3c71ad61810c1a12761e2e3e060e352f35`), riga
  `run tf_d7_p30 $P30 tf mtp 7`, il 25/10 02:23–02:34 CET, poi annotate con `tools/annotate_v11.py`. Il run usa gli stessi binari e flag.
- Binario `proxy/llama_spec_trace.v11.bin` (`f3f3ef188648ca9eb4d2d1a5331deba766203a438f70fe01b5d9f45bc5c037df`), librerie di
  `/workspace/llama.cpp/build/bin` (LLAMAFILE ON, come H-CA; **non** la build nollamafile della (a′)):
  libllama-common.so.0.7.0 `9823702776ab1afe…`, libllama.so.0.7.0 `e373ccc6…`, libggml-base `75b39048…`, libggml-cpu `e7879a7d…`,
  libggml `a5db187c…` (sha completi nel run file). Gli sha delle librerie all'epoca del tune H-CA non sono stati registrati; i loro mtime sono
  precedenti a quella run (01:41 CET del 25/10), ma l'identità non è dimostrata.
- Modello `models/qwen35-2b-mtp-q4_k_m.gguf` (`18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b`).
- Flag: `-m models/qwen35-2b-mtp-q4_k_m.gguf --spec-type draft-mtp --no-spec-draft-backend-sampling -t 6 --temp 0 -n 128 -c 8192 -b 8192 -ub 512
  --no-repack --dmax 7 --spec-draft-n-max 7 --mode tf --live-src mtp` → teacher-forced, MTP Dmax 7 + lookup ≤7, verify T=1, **cap 8**
  (T≤8), **greedy**. `-n 128` come H-CA: le correzioni più lunghe vengono troncate a 128 token.
- Formato: `annotate_v11.py` (`5940751543c5a6f4d1ec7e6a12f6173b1f5491a79578326f9a6d195588081df8`), schema strataplus.v1.1 (ref_tokens,
  cand.mtp, cand.lookup, acc.*, output_ids, domain), con `ANN_SPLIT=editfix_tune|editfix_holdout` e `ANN_REF_GLOB` sul tf stesso
  (ref = output proprio, verify T=1 = greedy T=1), come `run_check_v12.sh`. **domain = 'edit-fix', mai sommato a edit.** Nota: la stringa
  `label` scritta da annotate è "proxy CPU, non AMD" (codice di annotate, non modificato).
- Tag `editfix_tune_tf_d7` / `editfix_holdout_tf_d7`. I tag non iniziano con "holdout", perché annotate rinominerebbe quei file per dominio.

## 4. Cosa fa lo script (in ordine)
1. sha256 delle copie di `run_hlang_editfix.json` presenti (bbb9eb22… / dd1b8ee8…).
2. `sha256sum -c` di tracer, 5 librerie, modello, prompt, metadati, prep, LANG_LABEL_RULE, annotate, cpu_foreign, cpu_judge. Se uno è diverso: stop.
3. Verifica dello split e rigenerazione dei prompt (`--check`); confronto dei metadati, tranne il campo della fonte. Se diversi: stop.
4. `nollama`: se c'è un altro processo llama, stop. Poi `build_env_info.txt`: data, uname, lscpu, nproc, free, loadavg, gcc, cmake, python,
   pyarrow, git di llama.cpp, CMakeCache, env, sha256 di tutti gli input e dei parquet, ldd.
5. Per tune e poi holdout, una passata alla volta:
   - `nollama`;
   - comando in `cmds.txt`;
   - `cpu_foreign.py wait 30 0.5 3600` (precheck CPU libera);
   - monitor CPU ogni 2 s;
   - START/END in `campaign.log` e in `/workspace/strata-bench/cpu_busy_bench.log` (symlink a `strata-plus/cpu_busy_bench.log`; righe
     scritte dal mirror `tools/bench_window_log.py` se è vivo, altrimenti dallo script);
   - **un solo llama a nice 19**;
   - `cpu_judge` nella riga END;
   - stop se exit ≠ 0 o se il tracer salta un prompt.
6. Post, senza llama:
   - annotate per split;
   - validazione: 200 richieste, ids uguali al file dei prompt, domain `edit-fix`, 40 per linguaggio, greedy_equal_ref;
   - MANIFEST.sha256 in `strata-plus/traces/hlang_editfix_v1/{tune,holdout}/` e in `strata-plus/traces/raw/hlang_editfix_v1/`;
   - infine `hlang_editfix_v1.done`.
- Lo script rilancia senza ripetere le passate già finite (`.ok`). Durata: nessuna stima misurata. Per confronto, il tune H-CA (30 prompt) ha
  impiegato 11 min, ma questi prompt e il loro numero sono diversi.

## 5. Discrepanze / da confermare
- Template del prompt: scelto da Bench, **da confermare con Policy** prima del lancio.
- Run file H-CA assente in `runs/`: tracer e flag presi da `run_v11.sh`.
- sha delle librerie del tune H-CA non registrati all'epoca (sez. 3).
- Ordine: dopo le 10 build e la (a′) (AMD_PROTOCOL_v5 sez. 14).
- Serve `/tmp/venv_pa/bin/python` (pyarrow) per la verifica: si sovrascrive con `PYA=...`. Se manca, lo script si ferma prima di ogni llama.
