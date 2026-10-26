# Protocollo A/B Strata+ — speculative decoding su Qwen3.8-Flash-Next (bozza)

Stato: **bozza**. Tutti i riferimenti sono a `Niko1221/Strata` @ `7dd5cf18` (clone locale `/workspace/strata-src`).
Nessun numero AMD in questo file: i soli numeri misurati finora sono **proxy CPU** (vedi
`/workspace/strata-plus/traces/README.md`).

## 1. Cosa si misura
Per ogni config × dominio (code/chat/edit, + Spec-Bench e agentic sulle GPU):
- **AL** = token committati per round di verifica = (drafts accettati + round)/round — è la riga `speculation` di Strata
  (`src/program/generate.cpp:16727-16730`: "%.2f tokens per round").
- **tok/s di decode** (riga `decode … tok/s`, `generate.cpp:16874`) e **speedup** = tok/s(A)/tok/s(B) per prompt, appaiato
  nella stessa ripetizione ABBA.
- media, deviazione standard, IC95 (t di Student sulle differenze appaiate; bootstrap 2000 ricampionamenti come controllo).
- **accettati per verifica per categoria**: istogramma `accepted per round` (`generate.cpp:16758-16760`), suffix/lookup
  (`16739-16744`), `window sizes` con `--spec-min-p` (`16733-16737`).
- **uguaglianza greedy**: la riga `output  :` (id dei token, `generate.cpp:16867-16871`) di A deve essere identica a B.
  Strata è greedy per default (`--greedy`, `generate.cpp:423, 2455`); `--seed S` attiva il campionamento (`2456`): **mai** nei run A/B.

## 2. Matrice delle config
`--spec N` = finestra di verifica di N token = fino a N−1 draft MTP (help `generate.cpp:938`; default 0 = off, `656`).

| ID | Flag | Note (verificate nel codice) |
|---|---|---|
| **B** | `--spec 1` (o senza `--spec`) | nessuna speculazione |
| **A1** | `--spec 4 --spec-min-p 0.5` | finestra dinamica: estende finché la prob. del draft ≥ 0.5 (`generate.cpp:16540-16543`); suffix-draft attivo per default (`--suffix-draft 3`, `777`) |
| **A2** | A1 + `--lookup-chain 4` | dopo i draft MTP aggiunge fino a K draft di lookup (`16570-16582`; K ∈ [0,7], `2674`; min match 3, `784`) |
| **A3** | A1 + env `STRATA_SPEC_COST=1` | finestra cost-aware; attivo **solo** se il valore inizia per `1` (`generate.cpp:16402`, serve `11179`); quando è attivo prevale su `--spec-min-p` (`16538-16540`) |
| **A4** | A1 + `--suffix-draft 0` | solo MTP (il lookup del suffix si spegne, `16556`) |
| **A5** | solo lookup | in `generate` senza `--mtp` i draft vengono dall'oracolo (`16594-16595`), quindi **A5 si misura via `strata --serve`** (`generate.cpp:2637`) senza drafter MTP (DETAILS.md:148-151) — da confermare sul binario GPU |

Flag che **non esistono** con quel nome: nessuno dei quattro richiesti (`--spec`, `--spec-min-p`, `--lookup-chain`,
`STRATA_SPEC_COST`) manca; `STRATA_SPEC_COST` è una variabile d'ambiente, non un flag.

## 3. Ordine ABBA e ripetizioni
- Blocchi `B A A B` (per k config: B, A1..Ak, Ak..A1, B …) ripetuti R ≥ 3 volte; un blocco = tutti i prompt di un dominio.
- Warmup: 2 prompt scartati per processo; stesso processo/stessa sessione per tutti i prompt di una config.
- Fissi: `--max-new` (256 code/edit, 512 chat), `--max-context`, GPU, clock (`rocm-smi --setperfdeterminism` o
  `nvidia-smi -lgc` se disponibili), nessun altro carico; temperatura GPU registrata prima/dopo.
- Prompt: sottoinsiemi fissi (`DATASETS.md`, seed 20261025), tokenizzati una volta con il tokenizer del modello e
  passati come `--tokens-file` (`generate.cpp:2432`).

## 4. Registrazione (per ogni run)
`bench_ab.py` scrive `runs/<ts>/meta.json` (comando esatto, commit Strata `git rev-parse HEAD`, `git status`,
driver: `rocm-smi --showdriverversion`/`nvidia-smi`, `hipconfig --version`, kernel, CPU, env `STRATA_*`/`HIP_*`/`CUDA_*`),
`raw.jsonl` (una riga per prompt×config×rep con stdout/stderr completi e le metriche estratte), `summary.json/md`.
Per round: `STRATA_SPEC_TRACE=<file>` (già upstream, `generate.cpp:16398-16405`, "T a sfx ms p1 p2 …") e, con la patch
locale `patches/strata-plus-trace.patch` (non pushata), `STRATA_PLUS_TRACE=<file.jsonl>` in formato `strataplus.v1`
con tutte le candidate (MTP a profondità `--spec`−1 con probabilità, lookup anche se non scelto, token del target).

## 5. Criteri
- Greedy: 100% dei prompt identici a B, altrimenti la config è invalida (si indaga prima di guardare la velocità).
- Una config "vince" se l'IC95 dello speedup appaiato è tutto > 1 nel dominio.
- Variabilità: CV di B tra ripetizioni < 2%; altrimenti si rifà il blocco.

## 6. Cosa manca per lanciare
1. **Hardware**: questa box non ha GPU (8 core x86, ~16 GB RAM, nessuna swap) — servono le macchine R9700 / 7900 XTX /
   Strix Halo + una NVIDIA di riferimento. L'eseguibile `strata` richiede CUDA o HIP (`CMakeLists.txt:335`,
   `add_executable` a `759`); su CPU compila solo la libreria `strata_spec` (`1534-1536`, testata qui).
2. **Pesi**: Qwen3.8-Flash-Next (125B) non è scaricabile qui: 27.6–58.5 GB in memoria per Gyro-S, 54.8 GB IQ3_S
   (README.md:146-160); si scarica con `strata launch --model …` / setup (docs/MODELS.md:16, 269-275).
3. **Build GPU** (da validare sulle macchine, non eseguito qui):
   - ROCm (RDNA wave32): `cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_HIP=ON -DSTRATA_PREFILL_MMQ=ON -DCMAKE_HIP_ARCHITECTURES=<gfx1201|gfx1100|gfx1151>`
     (opzioni `CMakeLists.txt:82-83`, esempio completo in docs/GYRO.md:165-172, che aggiunge `-DSTRATA_GGML_DIR=$PWD/../agention-llama.cpp`; gfx1201 = R9700, gfx1100 = 7900 XTX, gfx1151 = Strix Halo;
     l'help dell'opzione dichiara validati gfx1100/gfx1201).
   - NVIDIA: `cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=<sm>`
     (opzione `CMakeLists.txt:69`; default arch 120, `182-183`).
   - poi `cmake --build build -j` e `git apply patches/strata-plus-trace.patch` (solo locale) per la traccia per round.
4. La patch `strata-plus-trace.patch` **non è compilata** (serve CUDA/HIP): va compilata e controllata su GPU.
5. A5 (lookup-only) via `--serve`: da scrivere il client e verificare il percorso.

## 7. Regola: sequenza singola per lookup-chain / gate_v2 (misure Strata su GPU)

- I run con `--lookup-chain` e con `gate_v2` si fanno **a sequenza singola**: niente `--batch`/`--slots`; con il server
  (`serve/server.py`) `"parallel": 1` (nessun `--batch N`), una richiesta alla volta.
- Nei metadati del run (§4) vanno registrati: `batch: none`, `parallel: 1`, il comando completo e la riga di avvio del server.
- L'harness **scarta il run** se nel log del processo `--serve` compare `BGEN` (o `BADM`): vuol dire che almeno una richiesta
  è passata dal percorso batch.
- Motivo (verificato nel codice da Scout, §6 di `/workspace/strata-plus/scout_patch_support.md`, Strata @`7dd5cf18`):
  - nel percorso batch (`batch_step`, slot `BSlot`) Strata usa **solo MTP**, senza suffix, lookup o `extra_draft_sources`;
  - un `BGEN` passa dal loop seriale solo per il primo token (`GEN 1`);
  - con `"parallel": N` una richiesta che si sovrappone a un'altra viene spostata in uno slot `BGEN`.
- Conseguenza: il guadagno di gate_v2 / lookup-chain misurato vale **solo per richieste servite da sole**.
  Non va esteso a carichi con richieste concorrenti.
