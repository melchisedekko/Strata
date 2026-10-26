import sys, pathlib
R = pathlib.Path('/workspace/strata-policy/pt12_worktree')
M = '// STRATA+ P-T12 measure'
def rep(path, old, new, count=1):
    p = R / path; s = p.read_text(); n = s.count(old)
    if n != count: sys.exit(f'{path}: expected {count} got {n}: {old[:90]!r}')
    p.write_text(s.replace(old, new))
G='src/program/generate.cpp'
rep(G, '''        std::vector<int64_t> t_cycle_n((size_t) o.spec + 1, 0), t_cycle_seen((size_t) o.spec + 1, 0);
''', f'''        std::vector<int64_t> t_cycle_n((size_t) o.spec + 1, 0), t_cycle_seen((size_t) o.spec + 1, 0);
        {M}: miss CPU per larghezza (ExpertDispatch::multi_misses / multi_entries, delta del round) e round con miss
        std::vector<int64_t> t_cycle_miss((size_t) o.spec + 1, 0), t_cycle_ent((size_t) o.spec + 1, 0),
            t_cycle_rmiss((size_t) o.spec + 1, 0);
''')
rep(G, '''            if (!ver.run(T, window.data(), p, &drive_pool_multi, &drive, outv.data(), err)) {
                // The graph of a window size is captured the first time it is used''',
f'''            const int64_t pt12_miss0 = drive.d.multi_misses, pt12_ent0 = drive.d.multi_entries;   {M}
            if (!ver.run(T, window.data(), p, &drive_pool_multi, &drive, outv.data(), err)) {{
                // The graph of a window size is captured the first time it is used''')
rep(G, '''            if (!t_cycle.empty() && timed_round && T <= o.spec && t_cycle_seen[(size_t) T]++ > 0) {
                t_cycle_ms[(size_t) T] += round_ms;
                ++t_cycle_n[(size_t) T];
            }''', f'''            if (!t_cycle.empty() && timed_round && T <= o.spec && t_cycle_seen[(size_t) T]++ > 0) {{
                t_cycle_ms[(size_t) T] += round_ms;
                ++t_cycle_n[(size_t) T];
                const int64_t pt12_dm = drive.d.multi_misses - pt12_miss0;   {M}
                t_cycle_miss[(size_t) T] += pt12_dm;
                t_cycle_ent[(size_t) T] += drive.d.multi_entries - pt12_ent0;
                if (pt12_dm > 0) ++t_cycle_rmiss[(size_t) T];
            }}''')
rep(G, '''                if (t_cycle_n[i] > 0) std::printf(" T%zu:%.2f(n=%lld)", i, t_cycle_ms[i] / (double) t_cycle_n[i], (long long) t_cycle_n[i]);
            std::printf("\\n");
''', f'''                if (t_cycle_n[i] > 0) std::printf(" T%zu:%.2f(n=%lld)", i, t_cycle_ms[i] / (double) t_cycle_n[i], (long long) t_cycle_n[i]);
            std::printf("\\n");
            std::printf("%-24s", "window CPU miss/round");   {M}: stessi round della riga sopra
            for (size_t i = 1; i < t_cycle_ms.size(); ++i)
                if (t_cycle_n[i] > 0)
                    std::printf(" T%zu:%.2f(entries=%.2f, rounds miss=%lld no-miss=%lld)", i,
                                (double) t_cycle_miss[i] / (double) t_cycle_n[i], (double) t_cycle_ent[i] / (double) t_cycle_n[i],
                                (long long) t_cycle_rmiss[i], (long long) (t_cycle_n[i] - t_cycle_rmiss[i]));
            std::printf("\\n");
''')
print('ok')
