# Protocollo AMD v5 (Strata+) — da eseguire sulla macchina AMD
Versione 5, 27/10/2026 ~13:45 CET. Copia della v4 (`AMD_PROTOCOL_v4.md`, sha256 1b26f43f4fcc269441e839b87ee5324197ea7ccb81b33e7b3489bacb34dc4c69,
**verificato** il 27/10 13:3x CET prima della copia, **non modificata**) con le modifiche elencate nella sez. M ("Modifiche rispetto a v4").
Valgono v1 → v2 → v3 → v4 → v5: **dove diverge prevale la v5**. Le sez. A–K della v3 restano valide salvo quanto scritto nella v4 e qui.

> **Il box non ha GPU AMD. Non esiste oggi nessun numero tok/s o s(T) misurato su AMD.** I valori di questo documento sono soglie
> pre-registrate, costanti di codice o sha256. I numeri CPU sono **proxy CPU, non AMD, llama.cpp non Strata** e non si trasferiscono.
> Nomenclatura: il dataset di edit con licenza non pubblicabile si chiama qui `edit_np`. Il suo tag nei nomi dei file è il valore locale
> `STRATAPLUS_EDIT_TAG` (`/workspace/lic_rm/edit_dataset.env`, mai pubblicato), lo stesso tag dei file esistenti (regola K della v3).

## M. Modifiche rispetto a v4
1. **Regola pronta-CPU** (sez. 2 e 3): sostituita dal testo di Strata Lead del 26/10 22:33 CET (citato alla lettera in sez. 3). La regola
   provvisoria non è più "stato massimo = archiviata finché mancano le build": si usa **solo** se il controllo senza patch non si linka nemmeno
   con ROCm 6.4.4, e in quel caso si riportano gli oggetti e il link resta al passo zero su AMD. Finché le build 6.4.4 non ci sono,
   nessuna patch è pronta-CPU (sono solo archiviate). La nota della v4/STATUS "regola provvisoria formulata da Bench, nessun testo del Lead"
   è superata.
2. **Tempi contaminati** (nuova sez. 13): ms e tok/s di agent_v12 (live_lookup, live_combo) e di E4 v14 (tutti i bracci tranne `full` sul
   dataset edit_np) sono CONTAMINATI da carico CPU estraneo e non si usano per decisioni; AL e accettazioni restano validi.
   Accordo Bench/Specu **confermato da Strata Lead il 27/10 13:34 CET**.
3. **Riferimento H-FC per `set_context`** (sez. 5): "v3 di H-FC" non esiste su disco; si cita `scout/patches/strataplus-HFC-frozen-v2.md`
   L68-70 (nome del file verificato), riferimento **confermato da Strata Lead il 27/10 13:34 CET**.
4. **Build e ordine rispetto alla (a′)** (sez. 2 e nuova sez. 14): 10 build in totale, una alla volta a nice 19 con ROCm 6.4.4, prima le 6 di
   Policy poi le 4 di Scout. **Ordine confermato da Strata Lead il 27/10 13:34 CET: le 10 build vanno tutte finite prima della (a′), senza
   sovrapposizioni**; la (a′) parte solo dopo la fine dell'ultima build e a CPU verificata libera. Sostituisce la frase della v4
   "10 build … dopo la fine della finestra (a′)".
5. Sez. 12 (riferimenti proxy) aggiornata di conseguenza. Nessun'altra sezione cambia; nessun numero nuovo misurato.

## 0. Cosa cambia rispetto alla v3 (testo della v4, invariato)
1. Binario di misura P-T12 e mappa dei commit riverificati (sez. 1).
2. Coda delle patch P0, P-HFC, P-H1, P-LANG, P-T12 con **due livelli**: pronta-CPU e fatta (sez. 2).
3. Regola pronta-CPU con ROCm 6.4.4 e regola provvisoria (sez. 3); passo zero AMD (sez. 4).
4. Bracci, percorsi e trace: costi congelati, percorso per round, `set_context`, H1 in pipeline T, serve-trace v1, regola overhead (sez. 5–7).
5. Modello e percorsi coperti (sez. 8); sha delle patch e file da non usare (sez. 9); identità greedy (sez. 10); soglie P0 (sez. 11).

## 1. Binario P-T12 e mappa dei commit
- **Binario di misura P-T12:** commit `e441f3a1338075889b3b96132ae86ad8688263ce` sul branch `strataplus-pt12-measure`
  (worktree /workspace/strata-policy/pt12_worktree, HEAD verificato il 27/10 13:2x CET). Gate e condizioni s(12): v3 sez. C–F, invariati.
  Patch archiviata: `strataplus/patches/bench/strataplus-PT12-measure-e441f3a.patch`, sha256 0ca997e2047ae60edbd37a9fe39e500564b5ee8e0601a15589b7ed8c70b0327c.
- **Rami non riscritti** (lic_rm/REWRITE_PLAN.md): `main` b24c6a1d8f2d12f9fc7221be57ee9bdc5811e8a0, `strataplus-pt12-measure` e441f3a1,
  `strataplus-policy-local` e467f6e2. I riferimenti a questi commit restano validi.
- **COMMIT_MAP (prima riscrittura, 26/10):** `/workspace/lic_rm/COMMIT_MAP_strataplus-research_2026-10-26.txt`,
  sha256 ba196e01b001b46a598e8fe1954a7b46babf20ed0758f310667b66cb6280de5d (**verificato**). Contiene `54002c144fc4f5674da175afafb279d8d5b5b9c1 → b5546916de278c1dd290f900417df09fae7169c9` (**verificato**, riga 4).
- **Terza passata (27/10):** `/workspace/lic_rm/COMMIT_MAP_strataplus-research_2026-10-27.txt`, sha256
  d9a7a89a78342d46f2f0fd096af73dbe9eb46a2695f66124c43bc4112878c758 (calcolato ora, 34 righe), contiene
  `b5546916de278c1dd290f900417df09fae7169c9 → 1f816f64b4e0cde5dba9c93de2dd474d8ccc059a`. Quindi sul branch `strataplus-research`
  di oggi il commit originale 54002c14 corrisponde a **1f816f64** (54002c14 → b5546916 → 1f816f64), non a b5546916.
  Il branch research dopo la passata era e4653ccb (REWRITE_PLAN); il backup locale è ora a d8b9113a (sync 27/10 13:21 CET).

## 2. Coda delle patch su due livelli
Definizioni: **pronta-CPU** = regola di Strata Lead del 26/10 22:33 CET (testo in sez. 3, sostituisce la formulazione della v4). **Fatta** = pronta-CPU + output greedy identico
alla baseline + A/B tok/s misurato su GPU AMD + .patch archiviato sul fork.

| ordine | patch | base / controllo | pronta-CPU | fatta | nota |
|---|---|---|---|---|---|
| 1 | **P0** (solo flag `--spec 8 --mtp-max-t 4`, nessuna patch) | stesso binario nei due bracci | no (nessun link ROCm 6.4.4 del controllo) | no | posizione in coda: sez. 11 (iv) |
| 2 | **P-HFC** (`strataplus-HFC-frozen-v2.patch`) | 7dd5cf1 | no (link `hfc_hip644_link.sh` non lanciato) | no | solo su AMD, dopo E-AMD-0 (v3 sez. I) |
| 3 | **P-H1** (`strataplus-H1-arbiter-v2.patch`) | b24c6a1d (`ctrl`) | no (build h1/h1st non lanciate) | no | soglie: plan/RULE_AMD_GO_PH1_PLANG.md |
| 4 | **P-LANG** (`strataplus-LANG-knob-v2.patch`, sopra H1 v2) | build `h1` | no (build full/fullst non lanciate) | no | prerequisiti: GO offline edit-fix e GO P-H1 su AMD |
| 5 | **P-T12** (misura, e441f3a) | 7dd5cf1 | no | no | non è nelle 10 build; gate v3 sez. C |

Stato verificato il 27/10 13:2x CET: non esistono `policy-local/logs/rocm644_v2/` né `scout-local/build644_*`. **Nessuna patch è pronta-CPU né fatta.**
Finché le build ROCm 6.4.4 non ci sono, **nessuna patch è pronta-CPU: sono solo archiviate** (v5, regola di sez. 3).
Ordine delle build (**v5**, sostituisce la v4): 10 build, una alla volta, **tutte finite prima della (a′)**, senza sovrapposizioni
(Strata Lead 27/10 13:34 CET): 6 di Policy (ctrl, h1, full, fullst, ctrlst, h1st), poi 4 di Scout (P-HFC v2, controllo 7dd5cf1, trace_ctl,
trace_hfc). Comandi e dettagli: sez. 14.

## 3. Regola pronta-CPU con ROCm 6.4.4, regola provvisoria, toolchain 5.7
- **Toolchain:** ROCm 6.4.4 in `/opt/rocm-6.4.4` (`.info/version` = 6.4.4-129; `hipcc --version`: HIP 6.4.43484-123eb5128, AMD clang 19.0.0git roc-6.4.4).
  L'env `/workspace/rocm-6.4.4.env` si carica **solo nelle shell di build** (mai nelle shell di misura né nel profilo globale).
- **Solo CUDA/HIP:** `generate.cpp` (cioè il binario `strata`) esiste solo con un backend GPU: CMakeLists.txt di 7dd5cf1 **L335**
  `if(STRATA_ENABLE_CUDA OR STRATA_ENABLE_HIP)` apre il blocco e **L759** `add_executable(strata src/program/generate.cpp)` è dentro quel blocco
  (verificato). Una build host senza GPU non compila `generate.cpp`: i test host non bastano per pronta-CPU.
- **Regola pronta-CPU (v5, testo di Strata Lead del 26/10 22:33 CET, sostituisce la formulazione della v4):**
  > "pronta-CPU = link completo del binario `strata` per gfx1100 e gfx1201 con ROCm 6.4.4 (/opt/rocm-6.4.4), patch e controllo compilati
  > con lo stesso comando, senza warning nuovi, più i test host. La regola provvisoria (`generate.cpp.o` e `strata_spec` per gfx1100, senza
  > warning nuovi rispetto al controllo) si usa solo se il controllo senza patch non si linka nemmeno con la 6.4; in quel caso per quella
  > patch si riportano gli oggetti e il link resta al passo zero su AMD."
- **Finché le build 6.4.4 non ci sono, nessuna patch è pronta-CPU (sono solo archiviate).** I controlli parziali (test host, sintassi,
  TU HIP singole con HIP 5.7) **non promuovono** nessuna patch a pronta-CPU e non si citano come "compila".
- Comando di riferimento (dalla v4, invariato): `cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_HIP=ON -DSTRATA_PREFILL_MMQ=ON
  "-DCMAKE_HIP_ARCHITECTURES=gfx1100;gfx1201"`, poi `ninja strata`; si registrano rc dei due lati e sha256 dei due binari.
- Una patch passata con la regola provvisoria **non è pronta-CPU**: si riportano gli oggetti (`generate.cpp.o`, `strata_spec`, gfx1100) e
  il link completo si fa al passo zero AMD (sez. 4).
- **Perché non HIP 5.7:** la toolchain Debian HIP 5.7 (clang++-17, `/usr/include/hip`) fallisce già sul controllo **7dd5cf1 senza patch**
  (scout-local/build_orig.log, verificato): `src/kernels/cuda/iq_kernels.cu:2477` ('alignas' attribute cannot be applied to types),
  `src/prefill/gemm.cu:970` (no matching function for call to 'ck'), `src/qwen35/q36_engine.cu:282` (no matching function for call to '__ldg').
  Un fallimento con 5.7 quindi non dice nulla sulla patch.

## 4. Passo zero AMD (prima di ogni sessione)
1. Patch e controllo si linkano **sulla macchina di misura**; si registrano versione di ROCm (`/opt/rocm*/.info/version`, `hipcc --version`),
   GPU (`rocminfo`/`rocm-smi`: nome, gfx, VRAM, driver), commit e sha256 dei due binari, comando di build completo.
2. Se il **controllo** non si linka, la sessione si ferma (nessuna misura della patch).
3. Per P0 (solo flag) i due bracci usano **lo stesso binario**: rc=0, sha256 registrato una volta.
4. Env completo di ogni processo da `/proc/<pid>/environ`; un solo processo `strata` per volta; macchina senza altri carichi GPU.

## 5. Bracci con costi congelati, percorso per round, set_context
- **Costi congelati in bracci separati.** `STRATA_SPEC_COST_FROZEN` (H-FC) e `STRATA_SPEC_JOINT_DET` (H1) non si accendono mai nello stesso
  processo. Con entrambi impostati H1 v2 esce con **rc=1 prima di caricare il modello**: `plus_h1_validate()` in generate.cpp
  **L1227-1232** sull'albero H1 v2 + LANG v2 (commit 560464ef; il controllo di conflitto è L1229-1232, chiamata a L2966; verificato).
  Sul commit solo-H1-v2 719b4d66 la stessa funzione è a L1221-1224 (verificato). Un rc=1 per questo motivo non è un guasto: è la guardia.
- **Percorso registrato per round:** ogni round si etichetta `serial` o `pipeline_t` (campo `path=` di serve-trace v1, sez. 6) e i risultati
  si riportano anche per percorso, con la quota di round in pipeline T.
- **`set_context`:** nel 7dd5cf1 il loop seriale chiama `policy.set_context(p)` (L14882) prima di choose (L14900), la CLI a L16537 prima di
  choose L16560; la **pipeline T non chiama `set_context`** (choose a L14471, verificato) e usa il bucket lasciato dall'ultimo `set_context`
  del loop seriale (all'inizio il bucket 0). È il comportamento descritto per H-FC in scout/patches/strataplus-HFC-frozen-v2.md (L68-70)
  e non va "corretto" durante la misura. Nota (v5): "v3 di H-FC" **non esiste su disco**; il riferimento è
  `/workspace/scout/patches/strataplus-HFC-frozen-v2.md` **L68-70** (nome verificato il 27/10 13:3x CET, sha256 del .md
  3ff97e28f6849ab1bf127f620aa65a7a297739ae2695883ffc8debf5a53c4eb9 calcolato ora; L68-70 = "Osservazione (comportamento di 7dd5cf1, non
  cambiato): il loop pipeline T non chiama `set_context` …"). Riferimento confermato da Strata Lead il 27/10 13:34 CET.
- **H1 in pipeline T senza JointHook:** in H1 v2 + LANG v2 la pipeline T chiama `policy.choose(w.T, …)` a **L14727** senza JointHook
  (JointHook solo a L11398 serve seriale e L16802 CLI; verificato). In pipeline T l'arbitro deterministico non agisce: il guadagno H1
  in pipeline T va riportato a parte e non si attribuisce a JOINT_DET.

## 6. serve-trace v1 e regola overhead
- **serve-trace v1** (`STRATA_SERVE_TRACE=<file>`, spento per default; una riga per round con `path=serial|pipeline_t`, req, lang, src, arb, frozen).
  4 varianti, sha256 **verificati ora** con i rispettivi `.sha256`:
  | variante | base | sha256 |
  |---|---|---|
  | strataplus-serve-trace-v1.patch | b24c6a1d (si applica anche su 7dd5cf1) | 2875566df6d7bffc7537465e726d861422ae2eb3e49d02b5bb7c24259ae02489 |
  | strataplus-serve-trace-v1-on-H1v2.patch | H1 v2 | 612c816f61b4821dd47edb9472ef43a7676fb2d4e15b810b430b2bbd0f2f6dda |
  | strataplus-serve-trace-v1-on-H1v2-LANGv2.patch | H1 v2 + LANG v2 | 3b8205a0bbd91602f942f33d063c44167825812aa329028224f27fe1f917382c |
  | strataplus-serve-trace-v1-on-HFCv2.patch | HFC v2 | 1a227fad6a9817f29c5dc1f537d212afc7ae159e296dcd141bd7a42fea93011f |
- **Dove si misura:** P-H1 e P-LANG **solo in serve**. P-HFC **in CLI e in serve**, riportati **separati** (mai sommati né mediati).
- **Regola overhead:**
  1. Il tok/s che decide il GO si misura con `STRATA_SERVE_TRACE` **spento in entrambi i bracci**.
  2. I dati per round vengono da run separate con il trace **acceso in entrambi i bracci**; non si mescolano con i tempi dell'A/B.
  3. Output greedy identico con trace acceso e spento (stesso binario, stessi prompt).
  4. L'overhead del trace (tok/s spento vs acceso) si riporta ma **non decide niente**. Oggi: overhead **non misurato**.

## 7. (vuota: i punti di misura per percorso sono nella sez. 5)

## 8. Modello e percorsi coperti
- Modello: **Qwen3.8-Flash-Next**, architettura GGUF `qwen4exp`, gira sul **percorso principale** di generate.cpp: in b24c6a1d il router
  (L2402-2412) imposta `qwen35 = model_family(meta) == Qwen35Moe` (**L2404** dichiarazione, L2407 confronto) e solo allora
  `return strata::qwen35::run(...)` (**L2411**); `qwen4exp` → `ModelFamily::Qwen4Exp` (include/strata/artifact/model_family.hpp L22), quindi
  resta sul percorso principale (verificato).
- `DraftPolicy` (albero H1 v2 + LANG v2): serve **L11396**, CLI **L16800** (verificato; nessun'altra istanza in generate.cpp).
- **Non coperti** dalle patch e dalla misura: `BGEN` / `--batch` (batch_step), il motore `qwen35` (src/qwen35) e i modelli `qwen35moe`.
  Un numero ottenuto su questi percorsi non vale per nessuna patch.

## 9. Sha delle patch e file da non usare
| patch | sha256 (verificato ora) | stato |
|---|---|---|
| scout/patches/strataplus-HFC-frozen-v2.patch | f5a02954320b39aaa6f385a3d5536dc9e25c2306d1248ed44ac9e61a6af355b5 | da misurare |
| strata-policy/patches/strataplus-H1-arbiter-v2.patch | e7b9b48cfe7f60388af076469e721b145957168005c5caea51b40edb0a1ba623 | da misurare |
| strata-policy/patches/strataplus-LANG-knob-v2.patch | 18122e6bd7696905d645c283c45cfb7c6e616b74ea43c1ec0f9f3f3d9287e2a8 | da misurare |
| strataplus-H1-arbiter-v1.patch | 9e54345ccb9159921971cd3bcd845ba79cdd212ee91b15459e4bc344f1c323e6 | **archiviata, non si misura** |
| strataplus-LANG-knob-v1.patch | 131fc71a0d33655aa67bead54dc6bc92d761e8a5b41c0a09cd42d3281d4e9724 | **archiviata, non si misura** |
| serve-trace v1 (4 varianti) | sez. 6 | strumento |
- **`lang_table_EXAMPLE_not_calibrated.json`** (policy-local/h1_worktree/strataplus/tests/, sha256 67c0daef…): **non si usa mai** per una misura,
  né per decidere né per "provare". La tabella P-LANG si calibra solo sullo split tune di edit-fix con tracce AMD, poi si congela e si hasha.
- In pipeline T una regola LANG `fixed` **può essere accorciata** dalla catena, che è draftata con il floor della pipeline (LANG v2 md, L49):
  la T effettiva per round si legge dal trace, non dalla tabella.

## 10. Identità greedy
- Script: `policy-local/h1_worktree/strataplus/tests/greedy_identity.py` (commit 560464ef, albero pulito),
  sha256 **7c1ffff5b9af430f79e90895f40382f0c57ebab23ab23a3814ee10fecfe0078e** (calcolato ora, 27/10 13:2x CET). Exit 0 = tutto identico,
  1 = una differenza, 2 = errore. Non è mai stato eseguito (carica un modello).
- Regola: output identico al controllo nel **100% dei prompt**; un solo prompt diverso ferma tutto (NO-GO e indagine).

## 11. Soglie P0 (flag-only `--spec 8 --mtp-max-t 4` contro la baseline, stesso binario)
- (a) greedy identico al **100%**;
- (b) **≥ +3% tok/s** con **limite inferiore IC95 > 0** (bootstrap per prompt, coppie alternate) **su code E su edit-fix**;
- (c) **chat non oltre −1%** (stima puntuale).
- Queste soglie **sostituiscono** per P0 il criterio "code o edit" della v3 (sez. B/H, E-AMD-0). Per H-LW (v3 sez. B) non cambia nulla.
- (iv) del Lead: un GO-proxy della run (a′) sul CPU **non cambia il default**: mette P0 **in testa** alla misura AMD. Senza GO-proxy
  P0 resta **in coda** (dopo le altre patch pronte). Il GO di P0 si decide solo su AMD con (a)–(c).
- Etichetta di ogni numero: AMD (nome GPU) oppure «proxy CPU, non AMD, llama.cpp non Strata».

## 12. Riferimenti proxy (solo contesto)
- Run (a′) v3: `/workspace/strata-bench/runs/run_live_combo_aprime_holdout_v3.sh` e `live_combo_aprime_holdout_v3.md` (sha256 nei rispettivi
  `.sha256`); v2 non modificata. Scritta, **non lanciata**. **v5:** si lancia solo dopo la fine di tutte e 10 le build (sez. 14) e a CPU
  verificata libera.
- Errata sui tempi MTP: `traces/ERRATA_mtp_process_ms_agent_v12_e4v14.md` (sha256 11aa7ebd371ad867b3286ee4686ee00c28fac70226b0fc74bb605a67e7dc6ffc).
- Regola edit_np (v3 sez. K) invariata: artefatti nuovi con dati per richiesta del dominio edit_np portano il tag locale nel nome; nei report
  solo aggregati per dominio.

## 13. Tempi contaminati da carico CPU estraneo (v5)
Accordo Bench/Specu, **confermato da Strata Lead il 27/10 13:34 CET**. Etichetta: proxy CPU, non AMD, llama.cpp non Strata.
- **CONTAMINATI** (ms e tok/s **non si usano per nessuna decisione**): agent_v12 bracci `live_lookup` e `live_combo`; E4 v14 **tutti i bracci
  tranne `full` sul dataset edit_np** (cioè full, dvocab, dvocab_en su code+chat e dvocab, dvocab_en su edit_np).
- **Validi:** AL e accettazioni (drafted/accepted) di tutte queste run.
- Il braccio E4 `full` su edit_np è l'unico con tempi puliti, ma **da solo non decide niente** (Strata Lead 27/10 13:34 CET).
- Agent_v12: tutti i tempi della serie erano già "non usabili come misura" (Lead 25/10 08:24, ERRATA sez. (a)); la v5 non cambia questo.
- Conteggi (criterio `tools/cpu_judge.py`: intervalli di 2 s con carico estraneo ≥ 0,5 core, picco in core, escluso sand-host). **Non sono
  nell'ERRATA** `traces/ERRATA_mtp_process_ms_agent_v12_e4v14.md` (sha256 11aa7ebd371ad867b3286ee4686ee00c28fac70226b0fc74bb605a67e7dc6ffc,
  verificato; l'errata tratta `mtp_process_ms`, non il carico CPU). Sono in `strata-bench/STATUS.md` (aggiornamento 27/10 13:3x, passo 2) e
  nelle righe END di `strata-plus/traces/raw/v11/campaign.log` (righe 275, 278, 287, 290, 293, 296, 299, 302, riletti ora; nessun ricalcolo):

| serie | braccio | intervalli ≥0,5 core | picco (core) | tempi |
|---|---|---|---|---|
| agent_v12 | live_lookup | 357 | 7,174 | CONTAMINATI |
| agent_v12 | live_combo | 751 | 8,041 | CONTAMINATI |
| E4 v14 | full (code+chat) | 20 | 4,948 | CONTAMINATI |
| E4 v14 | dvocab (code+chat) | 4 | 0,997 | CONTAMINATI |
| E4 v14 | dvocab_en (code+chat) | 2 | 1,136 | CONTAMINATI |
| E4 v14 | dvocab (edit_np) | 13 | 6,492 | CONTAMINATI |
| E4 v14 | dvocab_en (edit_np) | 22 | 4,832 | CONTAMINATI |
| E4 v14 | full (edit_np) | 0 | 0,17 | puliti (da soli non decidono) |

## 14. Build ROCm 6.4.4 e ordine rispetto alla (a′) (v5)
- **10 build in totale**, **una alla volta**, a **nice 19**, con ROCm 6.4.4 (`/opt/rocm-6.4.4`; env `/workspace/rocm-6.4.4.env` solo nelle shell di build):
  1. Policy: `bash /workspace/policy-local/hip_build_full_rocm644_v2.sh --bench-window-ended` — 6 build: ctrl, h1, full, fullst, ctrlst, h1st
     (script sha256 9145085c0bcfed5aa398aec076f0672cef46e7a280a9a3193ef0e6fdc852467c, calcolato ora; nice 19, `ninja -j2`).
  2. poi Scout: `/workspace/scout-local/hfc_hip644_link.sh` — 4 build: P-HFC v2, controllo 7dd5cf1, trace_ctl, trace_hfc
     (script sha256 9df20c13b73cb44f718022aa0f1d3d1069fe89ee9e2c4b3a5366828ee159c754, calcolato ora; nice 19, `-j2 -k 0`, sequenziali).
- **Ordine (Strata Lead, 27/10 13:34 CET): le 10 build vanno tutte finite prima della (a′), senza sovrapposizioni.** La (a′) parte solo dopo
  la fine dell'ultima build di Scout **e** a CPU verificata libera (`tools/cpu_foreign.py wait`, già nel run file v3). Nessuna build parte
  mentre gira una run di Bench, e viceversa.
- Nota sul flag: lo script di Policy rifiuta di partire senza `--bench-window-ended` e il suo messaggio d'uso dice "only after Bench announces
  the end of a'". Con l'ordine v5 il flag va letto come "nessuna finestra di Bench aperta": Bench lo annuncia prima di lanciare le build.
  Lo script non è stato modificato (non è di Bench).
- Stato al 27/10 13:3x CET (verificato): non esistono `policy-local/logs/rocm644_v2/` né `scout-local/build644_*`; nessuna build lanciata.
- Esito di ogni build secondo la regola di sez. 3: pronta-CPU solo con link completo di patch e controllo; regola provvisoria solo se il
  controllo non si linka con la 6.4.4 (lo script di Policy ha già il ramo "TOUCHED OBJECTS ONLY (control did not link)").
