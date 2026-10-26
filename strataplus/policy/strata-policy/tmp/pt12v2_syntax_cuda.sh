#!/usr/bin/env bash
# sintassi P-T12 v2 .cu, CUDA 12.9 header (wheel) con clang++-17 -x cuda sm_86: host-only + device-only (target-sdk 12.1), sequenziale
R=/workspace/strata-policy/pt12_worktree; cd $R; D=/workspace/rocm-hdr/cudaroot
OUT=/workspace/strata-policy/tmp/pt12v2_syntax_cuda_results.txt; : > $OUT
B="-x cuda --cuda-path=$D --cuda-gpu-arch=sm_86 -nocudalib -fsyntax-only -std=c++20 -DSTRATA_Q6K_EXPERTS=1 -DSTRATA_NATIVE_EXPERTS=1 -DSTRATA_HAVE_QWEN35=1 -I$R/include -I$R/third_party/ggml"
DEV="-U__FLOAT128__ -U__SIZEOF_FLOAT128__ -D__INTEL_LLVM_COMPILER=1 -DSYCL_LANGUAGE_VERSION=1 -Xclang -target-sdk-version=12.1"
for f in src/kernels/cuda/native_mmvq.cu src/kernels/cuda/native_bf16.cu src/kernels/cuda/shared_expert.cu src/kernels/cuda/s2_expert_grouped.cu src/kernels/cuda/fused_gr.cu src/kernels/cuda/verify_kernels.cu src/kernels/cuda/iq_kernels.cu; do
  clang++-17 $B --cuda-host-only $f > /tmp/pt12v2_c.txt 2>&1; echo "CUDA host-only $f rc=$? errors=$(grep -c ' error:' /tmp/pt12v2_c.txt)" >> $OUT; grep -m3 ' error:' /tmp/pt12v2_c.txt >> $OUT
  clang++-17 $B --cuda-device-only $DEV $f > /tmp/pt12v2_c.txt 2>&1; echo "CUDA device-only sm_86 $f rc=$? errors=$(grep -c ' error:' /tmp/pt12v2_c.txt)" >> $OUT; grep -m3 ' error:' /tmp/pt12v2_c.txt >> $OUT
done
# controllo negativo: un errore iniettato deve dare rc!=0
printf '#include "%s"\nstatic_assert(strata::kernels::kVerifyMaxT == 8, "neg");\n' $R/include/strata/kernels/verify_kernels.hpp > /tmp/pt12_neg.cu
clang++-17 $B --cuda-device-only $DEV /tmp/pt12_neg.cu > /tmp/pt12v2_c.txt 2>&1; echo "NEG device-only static_assert(kVerifyMaxT==8) rc=$? (atteso !=0)" >> $OUT
