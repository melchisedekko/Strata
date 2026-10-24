// src/spec/pool_source_test.cpp - Strata+ P4: the persistent pool survives reset(), gates short matches, evicts.
#include "strata/spec/pool_source.hpp"

#include <cstdio>
#include <cstdlib>
#include <vector>

namespace {
bool g_fail = false;
void check(bool ok, const char* what) {
    std::printf("  %-64s %s\n", what, ok ? "ok" : "FAIL");
    g_fail |= !ok;
}
}  // namespace

int main() {
    using strata::spec::PoolSource;
    std::vector<int32_t> a;
    for (int i = 0; i < 200; ++i) a.push_back(1000 + i);   // request 1: a distinctive run
    {
        PoolSource p(1 << 16, 12);
        p.append(a.data(), a.size());
        p.reset();                                          // request 2 starts
        std::vector<int32_t> r2 = {7, 8, 9};
        r2.insert(r2.end(), a.begin() + 50, a.begin() + 70);   // repeats 20 tokens of request 1
        p.append(r2.data(), r2.size());
        int32_t out[8]; int m = 0;
        const int k = p.propose(r2.data(), (int) r2.size(), 0, 8, out, &m);
        check(k > 0 && out[0] == a[70] && m >= 12, "pool: an earlier request's text is proposed after reset()");
        std::vector<int32_t> r3 = {5, 5, 5};
        r3.insert(r3.end(), a.begin() + 120, a.begin() + 125);   // only a 5-token repeat
        p.append(r3.data(), r3.size());
        const int k3 = p.propose(r3.data(), (int) r3.size(), 0, 8, out, &m);
        check(k3 == 0 && m == 0, "pool: matches shorter than the gate propose nothing");
    }
    {
        PoolSource p(2048, 12);
        p.append(a.data(), a.size());
        std::vector<int32_t> filler;
        for (int i = 0; i < 3000; ++i) filler.push_back(50000 + (i * 7919) % 40000);
        for (size_t i = 0; i < filler.size(); i += 100) p.append(filler.data() + i, 100);
        check(p.evictions() > 0 && p.size() <= 2048, "pool: capacity bounded, oldest text evicted");
        std::vector<int32_t> q(a.begin() + 50, a.begin() + 70);
        p.append(q.data(), q.size());
        int32_t out[8]; int m = 0;
        check(p.propose(q.data(), (int) q.size(), 0, 8, out, &m) == 0, "pool: evicted text is no longer proposed");
        std::vector<int32_t> f(filler.end() - 400, filler.end() - 380);
        p.append(f.data(), f.size());
        const int k = p.propose(f.data(), (int) f.size(), 0, 8, out, &m);
        check(k > 0 && out[0] == *(filler.end() - 380), "pool: indexing continues after eviction");
    }
    std::printf(g_fail ? "FAIL\n" : "PASS\n");
    return g_fail ? 1 : 0;
}
