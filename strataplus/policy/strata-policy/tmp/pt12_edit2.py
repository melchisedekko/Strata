import sys, pathlib
R = pathlib.Path('/workspace/strata-policy/pt12_worktree')
M = '// STRATA+ P-T12 measure'
def rep(path, old, new, count=1):
    p = R / path; s = p.read_text(); n = s.count(old)
    if n != count: sys.exit(f'{path}: expected {count} got {n}: {old[:90]!r}')
    p.write_text(s.replace(old, new))
N='src/kernels/cuda/native_mmvq.cu'
rep(N, f'default: throw std::invalid_argument("STRATA measurement patch: native MMVQ (wave, gfx906) requires 1 <= ncols <= 8");   {M}: guardia, ramo invariato',
       'default: throw std::invalid_argument("native MMVQ (wave) requires 1 <= ncols <= 8");')
F='src/kernels/cuda/fused_gr.cu'
rep(F, f'    if (split_on && a[0].s_down == nullptr && n_tok <= 8) {{   // its K-split down reads bf16 rows (not STRATA_HC_REQ8)   {M}: smem n_tok * GS_SL * 4',
       '    if (split_on && a[0].s_down == nullptr) {   // its K-split down reads bf16 rows (not STRATA_HC_REQ8)')
MS = M + ': guardia di misura, conservativa (costo dei miss a T>8 al più sovrastimato)'
P='src/kernels/cpu/pool.cpp'
helper = f'''{MS}
// Un job con nt > 8 token diventa job da <= 8 token consecutivi (stesso blob e fmt, act/nact/out agli stessi offset):
// i kernel CPU multi-token restano quelli esistenti (<= 8), il blob dell'expert viene letto una volta per blocco.
static bool pt12_split_over8(const ExpertJobMulti* jobs, int n, std::vector<ExpertJobMulti>& sub) {{
    bool any = false;
    for (int e = 0; e < n; ++e) any = any || jobs[e].nt > 8;
    if (!any) return false;
    sub.clear();
    for (int e = 0; e < n; ++e) {{
        const ExpertJobMulti& j = jobs[e];
        if (j.nt <= 8) {{ sub.push_back(j); continue; }}
        for (int t0 = 0; t0 < j.nt; t0 += 8) {{
            ExpertJobMulti s;
            s.blob = j.blob;
            s.fmt = j.fmt;
            s.nt = (std::min)(8, j.nt - t0);
            for (int t = 0; t < s.nt; ++t) {{
                s.act[t] = j.act[t0 + t];
                s.out[t] = j.out[t0 + t];
                s.nact[t] = j.nact[t0 + t];
            }}
            sub.push_back(s);
        }}
    }}
    return true;
}}

void ExpertPool::run_split_multi(ExpertJobMulti* jobs, int n) {{
    if (n <= 0) return;
    {{   {MS}
        std::vector<ExpertJobMulti> sub;
        if (pt12_split_over8(jobs, n, sub)) {{ run_split_multi(sub.data(), (int) sub.size()); return; }}
    }}
'''
rep(P, 'void ExpertPool::run_split_multi(ExpertJobMulti* jobs, int n) {\n    if (n <= 0) return;\n', helper)
rep(P, 'void ExpertPool::run_split_multi_native(const NativeFmt& f, ExpertJobMulti* jobs, int n) {\n    if (n <= 0) return;\n',
f'''void ExpertPool::run_split_multi_native(const NativeFmt& f, ExpertJobMulti* jobs, int n) {{
    if (n <= 0) return;
    {{   {MS}
        std::vector<ExpertJobMulti> sub;
        if (pt12_split_over8(jobs, n, sub)) {{ run_split_multi_native(f, sub.data(), (int) sub.size()); return; }}
    }}
''')
rep('src/prefill/prefill.cpp', '                                if (c <= strata::kernels::cpu::MAXT && (m.src->pinned(l, e) || !m.src->transient(l, e)))',
    f'                                if (c <= 8 && (m.src->pinned(l, e) || !m.src->transient(l, e)))   {M}: era cpu::MAXT (ora 12), il prefill resta a 8')
print('ok')
