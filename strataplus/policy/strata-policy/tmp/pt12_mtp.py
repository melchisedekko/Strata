import sys, pathlib
R = pathlib.Path('/workspace/strata-policy/pt12_worktree')
M = '// STRATA+ P-T12 measure (MTP opzionale)'
K = '::strata::kernels::kVerifyMaxT + 1'
def rep(path, old, new, count=1):
    p = R / path; s = p.read_text(); n = s.count(old)
    if n != count: sys.exit(f'{path}: expected {count} got {n}: {old[:90]!r}')
    p.write_text(s.replace(old, new))
H='include/strata/core/mtp.hpp'
rep(H, '#include "strata/kernels/sampler.hpp"\n', f'#include "strata/kernels/sampler.hpp"\n#include "strata/kernels/verify_kernels.hpp"   {M}: kVerifyMaxT\n')
rep(H, '    cudaGraphExec_t step_exec_[9] = {};\n', f'    cudaGraphExec_t step_exec_[{K}] = {{}};   {M}: [9] -> [kVerifyMaxT + 1] (aggiunta oltre la mappa: j fino a max_t - 2)\n')
rep(H, '    cudaGraphExec_t round_exec_c_[9] = {};\n    cudaGraphExec_t step_exec_c_[9] = {};\n',
    f'    cudaGraphExec_t round_exec_c_[{K}] = {{}};   {M}\n    cudaGraphExec_t step_exec_c_[{K}] = {{}};   {M}: aggiunta oltre la mappa\n')
rep(H, '    cudaGraphExec_t prefill_exec_[9] = {};\n    cudaGraphExec_t prefill_dev_exec_[9] = {};\n',
    f'    cudaGraphExec_t prefill_exec_[{K}] = {{}};   {M}\n    cudaGraphExec_t prefill_dev_exec_[{K}] = {{}};   {M}\n')
rep(H, '    cudaGraphExec_t round_exec_[9] = {};\n', f'    cudaGraphExec_t round_exec_[{K}] = {{}};   {M}\n')
C='src/core/mtp.cpp'
rep(C, '        xq_ = b.take<uint8_t>(strata::kernels::native_q8_1_bytes((int) (NH * HD), 8));\n',
    f'        xq_ = b.take<uint8_t>(strata::kernels::native_q8_1_bytes((int) (NH * HD), (int) std::max<uint64_t>(T, 8)));   {M}: 8 -> max(T, 8)\n')
rep(C, '''    if (round_exec_[T] == nullptr) { err = "mtp: chain graphs not prepared"; return false; }
    for (int j = 1; j < n_out; ++j)''', f'''    if (n_out > 8) {{ err = "mtp: chain n_out > 8 (ev_step_ / chain_tok_ / chain_prob_ hanno 8 posti)"; return false; }}   {M}: aggiunta oltre la mappa
    if (round_exec_[T] == nullptr) {{ err = "mtp: chain graphs not prepared"; return false; }}
    for (int j = 1; j < n_out; ++j)''')
print('ok')
