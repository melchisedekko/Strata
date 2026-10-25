// src/spec/joint_gate_test.cpp - Strata+ P5: the joint source+depth gate's basic behaviour.
#include "strata/spec/joint_gate.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>

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
        // (written for the full window: explicit tmax=8 since the default became arm A, tmax=5)
        JointGate::Options o8; o8.tmax = 8;
        JointGate g(o8);
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
    {   // bounds (Scout bug a): tmax = 8 plans windows up to T = 8 (rows 0..7) and no further; tmax > 8 is clamped;
        // an engine window T = 9 or d > 7 passed to observe() is folded into the last row, not written out of bounds
        JointGate::Options o; o.tmax = 8;
        JointGate g(o);
        const float hi[7] = {0.999f, 0.999f, 0.999f, 0.999f, 0.999f, 0.999f, 0.999f};
        const float hi9[9] = {0.999f, 0.999f, 0.999f, 0.999f, 0.999f, 0.999f, 0.999f, 0.999f, 0.999f};
        const int lu_acc[2] = {0, 0};
        int maxt = 0;
        for (int r = 0; r < 300; ++r) {
            JointGate::Choice c;
            if (g.start(none, 100, &c)) continue;
            int d = 0;
            while (true) { ++d; if (!g.keep(hi, nullptr, d)) break; }
            c = g.finish(hi, d, none);
            maxt = std::max(maxt, c.t);
            g.observe(c, c.t - 1, 1.0, 7, hi, none, lu_acc);   // flat cost: the widest window wins
        }
        check(maxt == 8, "tmax=8: the widest planned window is T=8 (kD drafts + 1)");
        JointGate::Choice c9; c9.src = JointGate::kMtp; c9.t = 9; c9.d = 8; c9.klu = 0;
        g.observe(c9, 8, 1.0, 8, hi9, none, lu_acc);   // must not touch memory past the 8 rows / 7 hazards
        check(std::isfinite(g.cost_pred(9, 0, 0)) && g.cost_pred(9, 0, 0) == g.cost_pred(8, 0, 0),
              "T=9 is priced (and learned) as the last measured row T=8");
        JointGate::Options o12; o12.tmax = 12;
        check(JointGate(o12).tmax() == 8, "tmax=12 is clamped to kD+1=8");
    }
    {   // seeded cost table (Scout bug b): frozen plans on the seeded s(T) and ignores later measurements
        JointGate g;
        const double s[8] = {1.0, 1.27, 1.51, 1.74, 1.98, 2.23, 2.47, 2.56};
        g.seed_costs(s, 0.26, 0.0, 43.0);
        g.set_frozen(true);
        const JointGate::Lookup none2[2] = {};
        const float lo[7] = {0.1f, 0.1f, 0.1f, 0.1f, 0.1f, 0.1f, 0.1f};
        const int lu_acc[2] = {0, 0};
        for (int r = 0; r < 50; ++r) {
            JointGate::Choice c;
            if (!g.start(none2, 100, &c)) c = g.finish(lo, 1, none2);
            g.observe(c, 0, 500.0, 0, lo, none2, lu_acc);   // wildly different measured cost
        }
        check(std::fabs(g.cost_pred(8, 0, 0) - 2.56 * 43.0) < 1e-9 && std::fabs(g.cost_pred(1, 2, 0) - 1.52 * 43.0) < 1e-9,
              "frozen: the gate plans on the seeded table (x unit), not the prior");
    }
    {   // rem bounded by the context window (Scout bug d)
        check(JointGate::remaining(100, 10, 4096, 200) == 89, "rem: max_new bound");
        check(JointGate::remaining(100, 10, 205, 200) == 4, "rem: context bound (max_context - p - 1)");
        check(JointGate::remaining(100, 10, 0, 200) == 89 && JointGate::remaining(5, 5, 0, 0) == 0, "rem: no bound / >= 0");
    }
    {   // arm A = the defaults (Strata Lead decision 25/10/2026): tmax=5, skip, prompt lookup only, no conf_stop
        const JointGate::Options d;
        check(d.tmax == 5 && d.skip && d.mtp && !d.conf_stop && d.use_src[0] && !d.use_src[1],
              "defaults = arm A: tmax=5, skip, mtp, lookup only, no conf_stop");
        JointGate g;
        check(g.tmax() == 5, "JointGate() has tmax 5");
        const float hi[7] = {0.999f, 0.999f, 0.999f, 0.999f, 0.999f, 0.999f, 0.999f};
        JointGate::Lookup lu[2] = {{7, 40, 1}, {}};
        const int lu_acc[2] = {7, 0};
        int maxt = 0, maxd = 0, maxlt = 0;   // klu = lookup PROPOSAL length (cost term), not the window
        for (int r = 0; r < 300; ++r) {   // flat cost, everything accepted: the widest allowed window wins
            JointGate::Choice c;
            const bool look = r % 3 == 0;
            if (!g.start(look ? lu : none, 100, &c)) {
                int dd = 0;
                while (true) { ++dd; if (!g.keep(hi, nullptr, dd)) break; }
                maxd = std::max(maxd, dd);
                c = g.finish(hi, dd, look ? lu : none);
            }
            maxt = std::max(maxt, c.t); maxd = std::max(maxd, c.d);
            if (c.src == JointGate::kLookup) maxlt = std::max(maxlt, c.t);
            g.observe(c, c.t - 1, 1.0, 7, hi, look ? lu : none, lu_acc);
        }
        check(maxt == 5 && maxd <= 4 && maxlt >= 2 && maxlt <= 5, "arm A: windows (MTP and lookup) reach T=5, never more; d<=4");
        unsetenv("STRATA_SPEC_JOINT");
        const bool off = !JointGate::enabled_from_env();
        setenv("STRATA_SPEC_JOINT", "0", 1);
        const bool zero = !JointGate::enabled_from_env();
        setenv("STRATA_SPEC_JOINT", "1", 1);
        const bool on = JointGate::enabled_from_env();
        unsetenv("STRATA_SPEC_JOINT");
        check(off && zero && on, "STRATA_SPEC_JOINT: unset/0 -> off (DraftPolicy), 1 -> on");
    }
    std::printf(g_fail ? "FAIL\n" : "PASS\n");
    return g_fail ? 1 : 0;
}
