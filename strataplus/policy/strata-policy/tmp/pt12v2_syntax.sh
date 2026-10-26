#!/usr/bin/env bash
# sintassi P-T12 v2: HIP 5.7.1 (clang++-17) e CUDA (g++ host, clang -x cuda per .cu); sequenziale
R=/workspace/strata-policy/pt12_worktree; cd $R
OUT=/workspace/strata-policy/tmp/pt12v2_syntax_results.txt; : > $OUT
HOST="src/core/verify.cpp src/kernels/cpu/pool.cpp src/prefill/prefill.cpp src/program/generate.cpp src/core/mtp.cpp src/core/expert_source.cpp src/kernels/cpu/expert.cpp src/kernels/cpu/native_expert.cpp src/core/remote_experts.cpp src/kernels/s2_expert_grouped_parity.cpp"
CU="src/kernels/cuda/native_mmvq.cu src/kernels/cuda/native_bf16.cu src/kernels/cuda/shared_expert.cu src/kernels/cuda/s2_expert_grouped.cu src/kernels/cuda/fused_gr.cu src/kernels/cuda/verify_kernels.cu src/kernels/cuda/iq_kernels.cu"
for f in $HOST; do
  [ -f $f ] || { echo "MISSING $f" >> $OUT; continue; }
  /workspace/rocm-hdr/check_hip.sh $R $f > /tmp/pt12v2_e.txt 2>&1; echo "HIP-host clang++-17 $f rc=$? $(grep -c 'error' /tmp/pt12v2_e.txt) err" >> $OUT; grep error /tmp/pt12v2_e.txt | head -3 >> $OUT
  /workspace/rocm-hdr/check_cuda.sh $R $f > /tmp/pt12v2_e.txt 2>&1; echo "CUDA-host g++ $f rc=$? $(grep -c 'error' /tmp/pt12v2_e.txt) err" >> $OUT; grep error /tmp/pt12v2_e.txt | head -3 >> $OUT
done
for f in $CU; do
  [ -f $f ] || { echo "MISSING $f" >> $OUT; continue; }
  clang++-17 -x hip --offload-arch=gfx1100 -nogpulib -fsyntax-only -std=c++20 -D__HIP_PLATFORM_AMD__=1 -DSTRATA_USE_HIP=1 -DSTRATA_WMMA_GFX11=1 -DSTRATA_Q6K_EXPERTS=1 -DSTRATA_NATIVE_EXPERTS=1 -DSTRATA_HAVE_QWEN35=1 -include $R/include/strata/hip_compat/cuda_runtime.h -I$R/include/strata/hip_compat -I$R/include -I$R/third_party/ggml $f > /tmp/pt12v2_e.txt 2>&1
  echo "HIP-device clang++-17 -x hip gfx1100 $f rc=$? $(grep -c 'error' /tmp/pt12v2_e.txt) err" >> $OUT; grep error /tmp/pt12v2_e.txt | head -3 >> $OUT
done
