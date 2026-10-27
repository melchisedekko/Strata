# P-HFC v2 — build HIP con ROCm 6.4.4 (gfx1100;gfx1201): esito

Data: 2026-10-27, START 15:02:09 CET, END 15:26:38 CET. Esecutore: Strata Scout. Macchina: box CPU del team (nessuna GPU AMD).

## Input
- Base: Niko1221/Strata @ 7dd5cf1 (MIT).
- Patch: `strataplus-HFC-frozen-v2.patch` sha256 `f5a02954320b39aaa6f385a3d5536dc9e25c2306d1248ed44ac9e61a6af355b5` (= sha di `git diff 7dd5cf1` nel worktree).
- Serve-trace: `strataplus-serve-trace-v1.patch` `2875566df6d7bffc7537465e726d861422ae2eb3e49d02b5bb7c24259ae02489`; `-on-HFCv2` `1a227fad6a9817f29c5dc1f537d212afc7ae159e296dcd141bd7a42fea93011f`.
- Script: `scripts/hfc_hip644_link.sh` sha256 `9df20c13b73cb44f718022aa0f1d3d1069fe89ee9e2c4b3a5366828ee159c754` (identico alla copia locale eseguita).

## Toolchain
- `hipcc --version`: HIP version 6.4.43484-123eb5128
- `/opt/rocm-6.4.4/llvm/bin/clang++ --version`: AMD clang version 19.0.0git (roc-6.4.4 25224 d366fa84f3fdcbd4b10847ebd5db572ae12a34fb)
- env caricato solo nel processo di build (`source /workspace/rocm-6.4.4.env`).

## Comandi (uguali per i 4 lati)
```
nice -n 19 cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_HIP=ON -DSTRATA_BUILD_TESTS=ON \
  -DCMAKE_HIP_COMPILER=/opt/rocm-6.4.4/llvm/bin/clang++ -DCMAKE_CXX_COMPILER=/opt/rocm-6.4.4/llvm/bin/clang++ \
  -DCMAKE_C_COMPILER=/opt/rocm-6.4.4/llvm/bin/clang "-DCMAKE_HIP_ARCHITECTURES=gfx1100;gfx1201" \
  "-DGPU_TARGETS=gfx1100;gfx1201" "-DAMDGPU_TARGETS=gfx1100;gfx1201" -DCMAKE_PREFIX_PATH=/opt/rocm-6.4.4 \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
nice -n 19 ninja -C build644_<lato> -j2 -k 0 strata
```
Lati: patch (7dd5cf1+HFCv2), ctl (7dd5cf1), trace_ctl (7dd5cf1+serve-trace-v1), trace_hfc (7dd5cf1+serve-trace-on-HFCv2). Una build alla volta.

## Esito
| lato | configure | ninja strata | binario `strata` |
|---|---|---|---|
| patch | 0 | 1 | assente |
| ctl | 0 | 1 | assente |
| trace_ctl | 0 | 1 | assente |
| trace_hfc | 0 | 1 | assente |

**Il controllo 7dd5cf1 non linka con ROCm 6.4.4.** Stessi 3 target FAILED in tutti e 4 i lati (`hip644_evidence_2026-10-27/link644_failed.txt`):
1. `src/kernels/cuda/iq_kernels.cu.o`: `'alignas' attribute cannot be applied to types` (L2477, L2664).
2. `src/prefill/gemm.cu.o`: ridefinizioni negli header ROCm 6.4.4 (`amd_hip_atomic.h` `Cond_t`, `unsafeAtomic*`, enum di `hipblas-common.h`).
3. `src/qwen35/q36_engine.cu.o`: `cublasSgemm`/`cublasGemmStridedBatchedEx` non dichiarati (L1555, L1961, L1975), `no matching function for call to '__ldg'` (L282).
Sono gli stessi 3 file che fallivano con HIP 5.7.

## Criterio di ripiego (regola provvisoria di Lead: controllo che non linka)
- Insieme FAILED: identico patch↔ctl e trace_hfc↔trace_ctl.
- Warning: 2841 righe per lato; i 4 file di warning hanno lo stesso sha256; `link644_w_diff.txt` e `link644_w_diff_trace.txt` vuoti. **Nessun warning nuovo.**
- Oggetti toccati dalla patch: `src/program/generate.cpp.o` compila in tutti e 4 i lati; `src/spec/draft_policy.cpp.o` compila e `libstrata_spec.a` viene creata in tutti e 4; `src/spec/serve_trace.cpp.o` compila in trace_ctl e trace_hfc; `sycl/src/program/generate.cpp` non fa parte della build HIP.
- Test host (build patch): `draft_policy_frozen_test` rc=0 PASS (39 ok); `draft_policy_test` rc=0 PASS (17 ok).

**Stato P-HFC v2: pronta-CPU per la regola provvisoria degli oggetti.** Il link completo resta il passo zero su AMD; «fatta» richiede identità greedy e A/B tok/s su GPU AMD.

## sha256 dei log (in scout-local, non pubblicati)
- hfc_hip644_link_run.log ccdcd2d5e4273663633df996e841850149475fc6b78788ca4a4d03a555daa5a5
- link644_build_patch.log 5ed4767a12a92a790c16da747302422f2dda1ef94029e5a5575cd23f0f31c137
- link644_build_ctl.log e96b758c8682709f7935961eb022bc29b7b587215a66eba537754b6cec2d522b
- link644_build_trace_ctl.log 7c999d8b134ea0bf5297755dd3628b08159a4f1eed94a6c90fff6e96b0298340
- link644_build_trace_hfc.log 952cfd9b437324057d744b44a66595b7d933afab71c394da0e02395d70800379
- link644_tests_patch.log 0e5d4d4978e345f522c661565857cc0de9f7461bc571466630239ad5ac29c3a0
- link644_failed.txt abda32277e03204a1bff102d97f5dd736fcb01a81e3a4f3adb572dd8c4e66fa8
