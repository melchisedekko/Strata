# AMD_PROTOCOL_v5 — addendum 1 (non modifica v5, sha256 b4a74287bbb2d7370aba02ccacb4c9c2cd13ae2a45d3d1d1ff07463c3b2d5e20)

Scritto: 2026-10-27 15:29:01 CET, su decisione di Strata Lead (15:28 CET).

## Esito delle 10 build ROCm 6.4.4 (HIP 6.4.43484-123eb5128, AMD clang 19.0.0git roc-6.4.4 25224 d366fa84)
- Policy (6 build, controllo b24c6a1d): controllo non linka. Patch h1, full, fullst, ctrlst, h1st: pronta-CPU con la regola provvisoria degli oggetti (rc=0 sugli oggetti toccati, stesso multiset di 131 warning).
- Scout (4 build, controllo 7dd5cf1, report scout/patches/strataplus-HFC-frozen-v2-hip644-RESULT.md sha256 1e776cf1e2d8757f954f2b61c594041f98a64e5357aa21a3b4adc74788a1e0d8): ninja rc=1 su tutti e 4 i lati, 2841 warning per lato con sha256 identico. P-HFC v2: pronta-CPU con la regola provvisoria degli oggetti, NON pronta-CPU piena, NON fatta (verdetto Lead).
- I conteggi di warning (131 contro 2841) non sono confrontabili tra loro: ogni build si confronta solo con il proprio controllo. Ogni report deve dichiarare target e comandi usati.

## Passo zero su AMD (integra v5 sez. 4, punti 1-2)
Il controllo senza patch, con ROCm 6.4.4 sul box CPU, fallisce su TRE file, tutti da verificare sulla macchina di misura:
1. src/kernels/cuda/iq_kernels.cu: errore 'alignas' a L2477 e L2664;
2. prefill/gemm.cu: ridefinizioni negli header di ROCm 6.4.4 (amd_hip_atomic.h, hipblas-common.h);
3. qwen35/q36_engine.cu: cublasSgemm e cublasGemmStridedBatchedEx non dichiarati, poi __ldg a L282.
Si registra per ciascuno rc, prima riga d'errore e sha256 del log. Se su AMD il controllo non si linka, la sessione si ferma (v5 sez. 4 punto 2), senza misure delle patch.

## Greedy identico (nota da diag_greedy_aprime, in verifica)
Sul proxy CPU l'identità greedy tra bracci dipende dal T massimo per round (kernel ggml-cpu tiled con rows >= 8; possibile FA split-KV con T=1 e n_kv >= 512). Al passo zero su AMD va verificato lo stesso effetto sui kernel HIP prima di applicare la soglia (ii). Il verdetto sulla causa è in diag_greedy_aprime_v1 (non ancora chiuso).
