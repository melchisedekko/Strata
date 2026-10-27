# Strata+: riepilogo della coda di patch

Ultimo aggiornamento: 27/10/2026 08:56 (ora di Roma, CET).

## 1. Obiettivo e definizioni

Vogliamo rendere più veloce lo speculative decoding di Strata (draft MTP più prompt lookup) su Qwen3.8-Flash-Next, su GPU AMD, senza cambiare l'output greedy. Sul box non c'è una GPU AMD. Per questo **nessuna patch ha ancora numeri AMD**, e i numeri CPU vengono solo dal proxy (llama.cpp, Qwen3.5-2B Q4_K_M).

- **Fatta**: la patch compila, l'output greedy è identico alla baseline, c'è un A/B tok/s misurato su GPU AMD e il file .patch è archiviato sul fork.
- **Pronta-CPU**: c'è il link completo di `strata` per gfx1100 e gfx1201 con ROCm 6.4.4 (`/opt/rocm-6.4.4`, env `/workspace/rocm-6.4.4.env`). La patch e il controllo sono compilati con lo stesso comando, la patch non aggiunge warning e i test host passano.
- **Misurata CPU-proxy**: esiste un numero dal proxy CPU, che non vale come misura AMD.
- **Archiviata**: il .patch è sul fork con il suo sha256 e ci sono controlli parziali (test host, sintassi o TU HIP). Manca il link completo con ROCm 6.4.4.

## 2. Stato delle patch

I percorsi sono relativi a `strataplus/` sul branch `strataplus-research`. Lo sha256 è abbreviato ai primi 12 caratteri.

| patch | autore | file sul fork + sha256 | base | cosa cambia | stato | soglia GO | prossimo passo |
|---|---|---|---|---|---|---|---|
| **P0** | Bench (run (a′)) | nessuna patch: solo flag `--spec 8 --mtp-max-t 4` | 7dd5cf1 | MTP a 4, finestra di verify e lookup fino a 8 | **non misurato**: la run (a′) sul proxy CPU è scritta ma non è stata lanciata | AMD (E-AMD-0): tok/s con CI95 > 0 in code o in edit, e nessuna cella W (cioè nessun peggioramento con CI95 < 0). Proxy: validità al 100%, coerenza ≥ 99%, AL entro ±3% dal replay, greedy identico | lanciare (a′) dopo E4; poi E-AMD-0 su AMD |
| **P-HFC** | Scout | `scout/scout/patches/strataplus-HFC-frozen-v2.patch`, `f5a02954320b` | 7dd5cf1 | `STRATA_SPEC_COST_FROZEN=<file>`: tabella dei costi fissa al posto dell'EMA, validata prima di caricare il modello. Esclude `STRATA_SPEC_JOINT_DET` | archiviata (test host PASS, 24/24 scenari) | stesso criterio di E-AMD-0. Solo su AMD, dopo E-AMD-0, con s(T) preso da P4 misurato su AMD in una sessione separata | link ROCm 6.4.4 (`hfc_hip644_link.sh`) |
| **P-H1** | Policy | `patches/strata-policy/strataplus-H1-arbiter-v2.patch`, `e7b9b48cfe7f` | b24c6a1d | P1–P6 più l'arbitro deterministico `STRATA_SPEC_JOINT_DET` nel loop seriale di serve e nella CLI. La pipeline-T usa solo i costi frozen | archiviata (build host + 8 test rc=0, TU HIP 5.7 gfx1100 con 131 warning, uguali al controllo) | (`plan/RULE_AMD_GO_PH1_PLANG.md`) build `h1` contro `ctrl` con `STRATA_SPEC_JOINT=1 STRATA_SPEC_JOINT_DET=1`: almeno +3% di tok/s in almeno un dominio con limite basso IC95 > 0; nessun dominio con stima puntuale sotto −1%; output greedy identico | build (2) h1 e (6) h1st, poi A/B su AMD |
| **P-LANG** | Policy | `patches/strata-policy/strataplus-LANG-knob-v2.patch`, `18122e6bd769` | b24c6a1d + H1-v2 | manopola per linguaggio (`--spec-lang-table` / `STRATA_SPEC_LANG_TABLE`, campo `strata_lang`), solo in serve. La tabella di esempio non è calibrata | archiviata (lang_knob_test 21 ok, serve 4/4, TU HIP con 131 warning, uguali al controllo) | (`plan/RULE_AMD_GO_PH1_PLANG.md`) solo dopo il GO offline edit-fix e il GO di P-H1 su AMD. Build `full`, con la tabella calibrata sullo split tune e poi congelata, contro `h1`: su edit-fix holdout almeno +3% di tok/s con limite basso IC95 > 0; su code e chat stima puntuale non sotto −1%; output identico | build (3) full e (4) fullst; calibrare la tabella sullo split tune con tracce AMD, poi congelarla e fare l'hash |
| **P-T12** | Bench (misura) | `patches/bench/strataplus-PT12-measure-e441f3a.patch`, `0ca997e2047a`; branch `strataplus-pt12-measure` (e441f3a) | 7dd5cf1 | serve solo a misurare s(12) (finestra > 8). Non è una patch di produzione | archiviata (sintassi HIP/CUDA rc 0; il test di parità 4b non è stato eseguito) | prima il gate: parità g_fail=0, registri e occupancy uguali, greedy identico per T da 1 a 8, s(T≤8) entro ±1%. Poi: se vince (a′), s(12)/s(8) ≤ 1,3645 in code o ≤ 1,3306 in edit; se vince il default, s(12)/s(6) ≤ 1,7813 in code o ≤ 1,7114 in edit. Il verdetto finale è l'A/B AMD | build e gate su AMD; non è nella coda dei 10 build |
| **serve-trace v1** | Policy | `patches/strata-policy/strataplus-serve-trace-v1.patch` `2875566df6d7`; `-on-H1v2` `612c816f61b4`; `-on-H1v2-LANGv2` `3b8205a0bbd9`; `-on-HFCv2` `1a227fad6a98` | b24c6a1d (si applica anche su 7dd5cf1) | `STRATA_SERVE_TRACE=<file>`, spento per default: scrive una riga per round con `path=serial` o `pipeline_t`, insieme a req, lang, src, arb e frozen | archiviata (test 22/22, ctest host 4/4, sintassi HIP ok). Overhead non misurato | nessuna: è uno strumento. Va solo verificato che l'output greedy sia identico con trace on e off | build (4) fullst, (5) ctrlst, (6) h1st e Scout trace_ctl / trace_hfc |

Nessuna patch è **pronta-CPU** né **fatta**. Nessuna patch è **misurata CPU-proxy**.

## 3. Build e misura

Stato della catena Bench, controllato il 27/10 alle 08:54 (ora di Roma, CET):
- `traces/raw/agent_v12/runs.done` è stato scritto alle 08:49:59 e `traces/agent_v12/AGENT_V12_READY` alle 08:50:07.
- E4 (`run_e4_v14.sh`) è partito alle 08:50 ed era ancora in corso alle 08:54: `e4v14.done` non esiste ancora.
- La run (a′) non è stata lanciata: la cartella `traces/raw/aprime_holdout_v14/` non esiste.

Le build ROCm 6.4.4 vanno lanciate **solo dopo la fine di E4 e della (a′)**, una alla volta, con nice 19. Nessuna è ancora partita: non ci sono i log `logs/rocm644_v2/` né `build644_*`.

1. Policy: `/workspace/policy-local/hip_build_full_rocm644_v2.sh --bench-window-ended`.
   - Fa 6 build in sequenza: ctrl (b24c6a1d), h1, full (H1+LANG), fullst, ctrlst, h1st.
   - Usa per tutte lo stesso comando: `nice -n 19 cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_HIP=ON -DSTRATA_PREFILL_MMQ=ON "-DCMAKE_HIP_ARCHITECTURES=gfx1100;gfx1201" …`, poi `nice -n 19 ninja -j2 strata`.
   - Lo script si rifiuta di partire se è attivo un processo aprime.
   - Il riepilogo va in `policy-local/logs/rocm644_v2/summary.txt`: rc, comando, warning rispetto al controllo e sha256 del binario.
2. Scout: `/workspace/scout-local/hfc_hip644_link.sh` (con `DRY=1` stampa solo i comandi).
   - Compila in sequenza patch (HFC v2) e ctl (7dd5cf1), poi i test host, poi trace_ctl e trace_hfc.
   - Per tutte usa `ninja -j2 -k 0 strata`.
   - Confronta i warning e stampa lo sha256 dei binari.

Questi sono 10 binari in tutto: 6 di Policy e 4 di Scout, come conferma `plan/RULE_AMD_GO_PH1_PLANG.md`.

## 4. Regole del protocollo AMD

- Il GO lo decide solo l'A/B tok/s su AMD, con il trace **spento in entrambi i bracci**. Le coppie sono alternate e il criterio è quello di E-AMD-0.
- I dati per round vengono da run separate con il trace acceso. Non si mescolano con i tempi dell'A/B.
- L'output greedy deve essere identico con il trace acceso e con il trace spento.
- Per ogni round si registra il path usato: loop seriale o pipeline-T.
- Passo zero: si usa la stessa build per i due bracci, si controlla rc=0 e si registra la versione di ROCm.
- Ordine: prima E-AMD-0 (bracci `--spec 4`, `--spec 8 --mtp-max-t 4`, `--spec 6`), poi P4 s(T), poi il gate P-T12 e s(12), poi H-LW. Il braccio H-FC è facoltativo e va dopo E-AMD-0.

## 5. Voci tagliate

- **Replay CPU di H-FC**: su CPU non si misura la velocità. Il replay conterebbe solo le scelte di T che cambiano (`scout_spec_HFC_v2.md` §5), quindi H-FC si valuta solo su AMD.
- **Tetto H-LANG(2)**: Scout non ha trovato nessun drafter sintattico adottabile che lasci identico l'output greedy. Anche un tetto ≥ 6% non avrebbe dato una patch misurabile entro il giro successivo. Con il cambio di passo, ciò che non arriva a una patch si taglia (`plan/RULE_AMD_GO_PH1_PLANG.md`). Il tetto non è mai stato misurato; la regola resta in archivio in `plan/RULE_HLANG2_ceiling.md`.

## 6. Dove guardare

- `README.md`: struttura del backup.
- `plan/piano.md` e `plan/PLAN_PAGE.md`: piano, ipotesi e criteri.
- `plan/RULE_AMD_GO_PH1_PLANG.md`: soglie GO su AMD per P-H1 e P-LANG, e motivo del taglio di H-LANG(2).
- `bench/strata-bench/STATUS.md`: stato delle run Bench.
- `.md` accanto a ogni patch: dettagli, test e numeri di riga.
