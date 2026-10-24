// src/spec/joint_gate_test.cpp - Strata+ P5: the joint source+depth gate's basic behaviour.
#include "strata/spec/joint_gate.hpp"

#include <cmath>
#include <cstdio>

namespace {
bool g_fail = false;
void check(bool ok, const char* what) {
    std::printf("  %-64s %s\n", what, ok ? "ok" : "FAIL");
    g_fail |= !ok;
}
}  // namespace

int main() {
    using strata::spec::JointGate;
    const JointGate::Lookup none[2] = {};
    {   // confident MTP chains on a flat verify cost are drafted deep; unconfident ones stop early
        JointGate g;
        const float hi[7] = {0.999f, 0.999f, 0.999f, 0.999f, 0.999f, 0.999f, 0.999f};
        const float lo[7] = {0.1f, 0.1f, 0.1f, 0.1f, 0.1f, 0.1f, 0.1f};
        for (int r = 0; r < 300; ++r) {   // learn: hi chains accept fully, lo chains fail at once; flat cost 1.0
            JointGate::Choice c;
            if (g.start(none, 100, &c)) continue;
            const bool h = r % 2 == 0;
            int d = 0;
            while (true) { ++d; if (!g.keep(h ? hi : lo, nullptr, d)) break; }
            c = g.finish(h ? hi : lo, d, none);
            const int acc = h ? c.t - 1 : 0;
            const int lu_acc[2] = {0, 0};
            g.observe(c, acc, 1.0 + 0.05 * c.d, h ? 7 : 0, h ? hi : lo, none, lu_acc);
        }
        JointGate::Choice c;
        int dh = 0, dl = 0;
        if (!g.start(none, 100, &c)) { while (true) { ++dh; if (!g.keep(hi, nullptr, dh)) break; } }
        if (!g.start(none, 100, &c)) { while (true) { ++dl; if (!g.keep(lo, nullptr, dl)) break; } }
        check(dh >= 5, "depth: confident chains are drafted deep under a flat cost");
        check(dl == 1, "depth: an unconfident first draft stops the chain");
        const JointGate::Choice ch = g.finish(hi, dh, none);
        check(ch.src == JointGate::kMtp && ch.t == dh + 1, "source: the confident chain is verified whole");
    }
    {   // lookup-first: a lookup that keeps being right is taken without drafting the MTP
        JointGate g;
        const float mid[7] = {0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f, 0.5f};
        JointGate::Lookup lu[2] = {{7, 30, 1}, {}};
        int skipped = 0;
        for (int r = 0; r < 200; ++r) {
            JointGate::Choice c;
            const bool sk = g.start(lu, 100, &c);
            if (!sk) { int d = 0; while (true) { ++d; if (!g.keep(mid, nullptr, d)) break; } c = g.finish(mid, d, lu); }
            skipped += sk && c.src == JointGate::kLookup;
            const int a = c.src == JointGate::kLookup ? c.t - 1 : 0;
            const int lu_acc[2] = {7, 0};
            g.observe(c, a, 1.0 + 0.3 * (c.t - 1), 0, mid, lu, lu_acc);
        }
        check(skipped > 150, "lookup-first: a reliable long lookup skips the MTP draft");
    }
    {   // H4 variant: the entropy stop
        JointGate::Options o; o.conf_stop = true;
        JointGate g(o);
        const float p[7] = {0.9f, 0.9f, 0.9f, 0.9f, 0.9f, 0.9f, 0.9f};
        const float ent[7] = {0.05f, 0.05f, 2.0f, 0.05f, 0.05f, 0.05f, 0.05f};
        JointGate::Choice c;
        int d = 0;
        if (!g.start(none, 100, &c)) { while (true) { ++d; if (!g.keep(p, ent, d)) break; } }
        check(d == 3, "conf_stop: drafting stops at the first high-entropy draft");
    }
    std::printf(g_fail ? "FAIL\n" : "PASS\n");
    return g_fail ? 1 : 0;
}
