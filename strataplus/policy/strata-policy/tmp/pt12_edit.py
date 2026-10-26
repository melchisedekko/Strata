import sys, pathlib
R = pathlib.Path('/workspace/strata-policy/pt12_worktree')
M = '// STRATA+ P-T12 measure'
def rep(path, old, new, count=1):
    p = R / path
    s = p.read_text()
    n = s.count(old)
    if n != count:
        sys.exit(f'{path}: expected {count} got {n} for: {old[:80]!r}')
    p.write_text(s.replace(old, new))

# (3) verifier host
rep('include/strata/kernels/verify_kernels.hpp', 'inline constexpr int kVerifyMaxT = 8;',
    f'inline constexpr int kVerifyMaxT = 12;   {M}: 8 -> 12 (solo misura s(12)/s(8))')
rep('include/strata/kernels/cpu/expert.hpp', 'inline constexpr int MAXT = 8;',
    f'inline constexpr int MAXT = 12;   {M}: 8 -> 12 (MAXT * 10 = 120 <= 128)')
V = 'include/strata/core/verify.hpp'
rep(V, '#include "strata/kernels/sampler.hpp"\n', f'#include "strata/kernels/sampler.hpp"\n#include "strata/kernels/verify_kernels.hpp"   {M}: kVerifyMaxT per gli array sotto\n')
K = '::strata::kernels::kVerifyMaxT'
rep(V, 'double prof_t_sum_[9][2][kProfPer] = {};', f'double prof_t_sum_[{K} + 1][2][kProfPer] = {{}};   {M}: [9] -> [kVerifyMaxT + 1]\n   ')
rep(V, 'int64_t prof_t_win_[9] = {};', f'int64_t prof_t_win_[{K} + 1] = {{}};   {M}')
rep(V, 'int32_t last_tokens_[8] = {};', f'int32_t last_tokens_[{K}] = {{}};   {M}: [8] -> [kVerifyMaxT]')
rep(V, 'cudaGraphExec_t exec_[9] = {};', f'cudaGraphExec_t exec_[{K} + 1] = {{}};   {M}')
rep(V, 'cudaGraphExec_t exec_nr_[9] = {};', f'cudaGraphExec_t exec_nr_[{K} + 1] = {{}};   {M}\n   ')
rep(V, 'bool launched_[9] = {}, launched_nr_[9] = {};', f'bool launched_[{K} + 1] = {{}}, launched_nr_[{K} + 1] = {{}};   {M}\n   ')
rep(V, 'int groups_[9] = {};', f'int groups_[{K} + 1] = {{}};   {M}')
C = 'src/core/verify.cpp'
rep(C, '    for (int T = 1; T <= 8; ++T) {\n        if (prof_t_win_[T] == 0) continue;',
    f'    for (int T = 1; T <= strata::kernels::kVerifyMaxT; ++T) {{   {M}: 8 -> kVerifyMaxT\n        if (prof_t_win_[T] == 0) continue;')
rep(C, '    if (last_t_ >= 1 && last_t_ <= 8) {\n        for (int k = 0; k < 2; ++k)',
    f'    if (last_t_ >= 1 && last_t_ <= strata::kernels::kVerifyMaxT) {{   {M}: 8 -> kVerifyMaxT\n        for (int k = 0; k < 2; ++k)')

# (2) MTP
H = 'include/strata/core/mtp.hpp'
rep(H, '#include "strata/kernels/sampler.hpp"\n', f'#include "strata/kernels/sampler.hpp"\n#include "strata/kernels/verify_kernels.hpp"   {M}: kVerifyMaxT per gli array dei grafi\n')
rep(H, 'cudaGraphExec_t step_exec_[9] = {};', f'cudaGraphExec_t step_exec_[{K} + 1] = {{}};   {M}: j fino a max_t - 2 (10 a T 12)')
rep(H, 'cudaGraphExec_t round_exec_c_[9] = {};', f'cudaGraphExec_t round_exec_c_[{K} + 1] = {{}};   {M}')
rep(H, 'cudaGraphExec_t step_exec_c_[9] = {};', f'cudaGraphExec_t step_exec_c_[{K} + 1] = {{}};   {M}')
rep(H, 'cudaGraphExec_t prefill_exec_[9] = {};', f'cudaGraphExec_t prefill_exec_[{K} + 1] = {{}};   {M}')
rep(H, 'cudaGraphExec_t prefill_dev_exec_[9] = {};', f'cudaGraphExec_t prefill_dev_exec_[{K} + 1] = {{}};   {M}')
rep(H, 'cudaGraphExec_t round_exec_[9] = {};', f'cudaGraphExec_t round_exec_[{K} + 1] = {{}};   {M}')
P = 'src/core/mtp.cpp'
rep(P, 'xq_ = b.take<uint8_t>(strata::kernels::native_q8_1_bytes((int) (NH * HD), 8));',
    f'xq_ = b.take<uint8_t>(strata::kernels::native_q8_1_bytes((int) (NH * HD), (int) std::max<uint64_t>((uint64_t) T, 8)));   {M}: >= T colonne')
rep(P, '    if (round_exec_[T] == nullptr) { err = "mtp: chain graphs not prepared"; return false; }\n',
    f'    if (n_out > 8) {{ err = "STRATA measurement patch: MTP chain with n_out > 8 (chain_tok_[8], ev_step_[8])"; return false; }}   {M}\n'
    '    if (round_exec_[T] == nullptr) { err = "mtp: chain graphs not prepared"; return false; }\n')

# (4) GPU
N = 'src/kernels/cuda/native_mmvq.cu'
rep(N, 'constexpr int MAX_NCOLS = 8;', f'constexpr int MAX_NCOLS = 12;   {M}: 8 -> 12')
rep(N, '''        case 8: launch_multi_n<F, 8>(weights, x_q8_1, y, n_in, n_out, s); break;
        default: throw std::invalid_argument("native MMVQ multi-column launch requires 2 <= ncols <= 8");''',
f'''        case 8: launch_multi_n<F, 8>(weights, x_q8_1, y, n_in, n_out, s); break;
        case 9: launch_multi_n<F, 9>(weights, x_q8_1, y, n_in, n_out, s); break;     {M}
        case 10: launch_multi_n<F, 10>(weights, x_q8_1, y, n_in, n_out, s); break;   {M}
        case 11: launch_multi_n<F, 11>(weights, x_q8_1, y, n_in, n_out, s); break;   {M}
        case 12: launch_multi_n<F, 12>(weights, x_q8_1, y, n_in, n_out, s); break;   {M}
        default: throw std::invalid_argument("native MMVQ multi-column launch requires 2 <= ncols <= 12");   {M}''')
rep(N, 'if (ncols < 1 || ncols > MAX_NCOLS) throw std::invalid_argument("native MMVQ requires 1 <= ncols <= 8");',
    f'if (ncols < 1 || ncols > MAX_NCOLS) throw std::invalid_argument("native MMVQ requires 1 <= ncols <= 12");   {M}')
rep(N, 'default: throw std::invalid_argument("native MMVQ (wave) requires 1 <= ncols <= 8");',
    f'default: throw std::invalid_argument("STRATA measurement patch: native MMVQ (wave, gfx906) requires 1 <= ncols <= 8");   {M}: guardia, ramo invariato')
rep(N, '''bool q8_packed_mmvq(const void* weights, const void* x_q8_1, float* y, int n_in, int n_out, int ncols, void* stream) {
''', f'''bool q8_packed_mmvq(const void* weights, const void* x_q8_1, float* y, int n_in, int n_out, int ncols, void* stream) {{
    if (ncols > 8) return false;   {M}: il packed ha ncols <= 8, oltre resta il layout GGUF
''')
rep(N, '''bool q6_packed_mmvq(const void* weights, const void* x_q8_1, float* y, int n_in, int n_out, int ncols, void* stream) {
''', f'''bool q6_packed_mmvq(const void* weights, const void* x_q8_1, float* y, int n_in, int n_out, int ncols, void* stream) {{
    if (ncols > 8) return false;   {M}: il packed ha ncols <= 8, oltre resta il layout GGUF
''')
S = 'src/kernels/cuda/shared_expert.cu'
rep(S, '''    if (n_tok < 1 || n_tok > 8 || !nw.q8_1 || !nw.gate_data || !nw.up_data || !nw.down_data || !stream)
        throw std::invalid_argument("shared_expert_multi: needs 1..8 tokens, native weights, scratch and a stream");''',
f'''    if (n_tok < 1 || n_tok > 12 || !nw.q8_1 || !nw.gate_data || !nw.up_data || !nw.down_data || !stream)   {M}: 8 -> 12
        throw std::invalid_argument("shared_expert_multi: needs 1..12 tokens, native weights, scratch and a stream");''')
B = 'src/kernels/cuda/native_bf16.cu'
rep(B, '''    if (n_tok < 1 || n_tok > 8 || n_in <= 0 || (n_in & 1) != 0 || n_out <= 0 || (ldx & 1) != 0 || x == nullptr ||
        w == nullptr || y == nullptr || (reinterpret_cast<uintptr_t>(x) & 7u) != 0)
        throw std::invalid_argument("bf16_gemv_fp32_mmvf_multi: 1..8 rows, even n_in/ldx, aligned pointers");''',
f'''    if (n_tok < 1 || n_tok > 12 || n_in <= 0 || (n_in & 1) != 0 || n_out <= 0 || (ldx & 1) != 0 || x == nullptr ||   {M}: 8 -> 12
        w == nullptr || y == nullptr || (reinterpret_cast<uintptr_t>(x) & 7u) != 0)
        throw std::invalid_argument("bf16_gemv_fp32_mmvf_multi: 1..12 rows, even n_in/ldx, aligned pointers");''')
rep(B, '    if (rows && n_out >= 64) {\n        const int ni = (int) n_in, no = (int) n_out;\n        switch (mmvf_block_size(n_in)) {\n            case 32: launch_rows<32>(x, ldx, w, y, ldy, ni, no, n_tok, st); break;',
    f'    if (rows && n_out >= 64 && n_tok <= 8) {{   {M}: launch_rows ha NT <= 8, oltre il kernel multi\n        const int ni = (int) n_in, no = (int) n_out;\n        switch (mmvf_block_size(n_in)) {{\n            case 32: launch_rows<32>(x, ldx, w, y, ldy, ni, no, n_tok, st); break;')
rep(B, '''        default: launch_pdl(bf16_f32_mmvf_multi_kernel<N, 8, false>, dim3((unsigned) n_out), dim3(N), 0, st, x, ldx, w, y, ldy, (int) n_in, n_tok); break; \\''',
'''        case 9: case 10: case 11: case 12: /* STRATA+ P-T12 measure: 9..12 righe */ \\
            launch_pdl(bf16_f32_mmvf_multi_kernel<N, 12, false>, dim3((unsigned) n_out), dim3(N), 0, st, x, ldx, w, y, ldy, (int) n_in, n_tok); break; \\
        default: launch_pdl(bf16_f32_mmvf_multi_kernel<N, 8, false>, dim3((unsigned) n_out), dim3(N), 0, st, x, ldx, w, y, ldy, (int) n_in, n_tok); break; \\''')
G = 'src/kernels/cuda/s2_expert_grouped.cu'
rep(G, 'constexpr int GMAX = 8;                          // entries per group (tokens routed to one expert in a window)',
    f'constexpr int GMAX = 12;                         // entries per group (tokens routed to one expert in a window)   {M}: 8 -> 12')
FH = 'include/strata/kernels/fused_gr.hpp'
rep(FH, 'constexpr int kFusedGrMaxT = 8;', f'constexpr int kFusedGrMaxT = 12;   {M}: 8 -> 12 (verify.cpp FusedGrArgs fa[kFusedGrMaxT] riempito per t < T)')
F = 'src/kernels/cuda/fused_gr.cu'
rep(F, '''struct GrMulti {
    FusedGrArgs a[kFusedGrMaxT];
    float* xn;
    int T;
};
''', f'''struct GrMulti {{
    FusedGrArgs a[kFusedGrMaxT];
    float* xn;
    int T;
}};
static_assert(sizeof(GrMulti) <= 4096, "GrMulti is passed by value: kernel parameters are limited to 4 KB");   {M}
''')
rep(F, '''        case 7: launch_q8_t<7>(m, part, ssg, st, stamp_buf, stamp_i0); break;
        default: launch_q8_t<8>(m, part, ssg, st, stamp_buf, stamp_i0); break;''',
f'''        case 7: launch_q8_t<7>(m, part, ssg, st, stamp_buf, stamp_i0); break;
        case 8: launch_q8_t<8>(m, part, ssg, st, stamp_buf, stamp_i0); break;   {M}: era il default (troncava T > 8)
        default:   {M}: guardia, STRATA_HC_Q8 non supporta T > 8
            std::fprintf(stderr, "STRATA measurement patch: fused_gr STRATA_HC_Q8 path called with T=%d > 8\\n", m.T);
            std::exit(1);''')
rep(F, '    if (split_on && a[0].s_down == nullptr) {   // its K-split down reads bf16 rows (not STRATA_HC_REQ8)',
    f'    if (split_on && a[0].s_down == nullptr && n_tok <= 8) {{   // its K-split down reads bf16 rows (not STRATA_HC_REQ8)   {M}: smem n_tok * GS_SL * 4')

# CPU guards
GUARD = '''    if ({v} > 8) {{   {M}: guardia, i kernel CPU restano a <= 8 token
        std::fprintf(stderr, "STRATA measurement patch: CPU expert path called with n_tok>8\\n");
        std::abort();
    }}
'''
NE = 'src/kernels/cpu/native_expert.cpp'
rep(NE, '''void native_gu_rows(const NativeFmt& f, const uint8_t* blob, const void* const* act, int nt, float* const* ff,
                    int r0, int r1) {
''', '''void native_gu_rows(const NativeFmt& f, const uint8_t* blob, const void* const* act, int nt, float* const* ff,
                    int r0, int r1) {
''' + GUARD.format(v='nt', M=M))
rep(NE, '''void native_down_rows(const NativeFmt& f, const uint8_t* blob, const void* const* hq, int nt, float* const* out,
                      int r0, int r1) {
''', '''void native_down_rows(const NativeFmt& f, const uint8_t* blob, const void* const* hq, int nt, float* const* out,
                      int r0, int r1) {
''' + GUARD.format(v='nt', M=M))
E = 'src/kernels/cpu/expert.cpp'
for sig, v in [
  ('void s2_expert_gu_rows_multi(const uint8_t* blob, const ActQ* const* a1, int n_tokens, float* const* ff, int r0,\n                             int r1) {\n', 'n_tokens'),
  ('void s2_expert_down_rows_multi(const uint8_t* blob, const ActQ* const* a2, int n_tokens, float* const* out, int r0,\n                               int r1) {\n', 'n_tokens'),
  ('void q2_0_gguf_rows_multi(const uint8_t* w, size_t row_bytes, int nblocks, const ActQ* const* a, int nt,\n                          float* const* out, int r0, int r1) {\n', 'nt'),
  ('void s2_expert_vnni_multi(const uint8_t* blob, const ActQ* const* a1, int n_tokens, float* const* out,\n                          ExpertScratchMulti& ws) {\n', 'n_tokens'),
]:
    rep(E, sig, sig + GUARD.format(v=v, M=M))
print('ok')
