#include "strata/spec/joint_gate.hpp"
#include <cstdio>
#include <cstring>
#include <cstdlib>
using strata::spec::JointGate;
int main(int argc, char** argv) {
    const JointGate::Lookup none[2] = {};
    const float hi[9] = {0.999f,0.999f,0.999f,0.999f,0.999f,0.999f,0.999f,0.999f,0.999f};
    const int lu_acc[2] = {0, 0};
    JointGate::Options o; o.tmax = std::atoi(argv[1]); JointGate g(o);
    if (!std::strcmp(argv[2], "start")) { for (int r = 0; r < 50; ++r) { JointGate::Choice c; if (!g.start(none, 100, &c)) { int d=0; while (d < 7 && g.keep(hi, nullptr, ++d)) {} c = g.finish(hi, d, none);} g.observe(c, c.t-1, 1.0, 7, hi, none, lu_acc);} }
    if (!std::strcmp(argv[2], "t9")) { JointGate::Choice c; c.src = 1; c.t = 9; c.d = 8; g.observe(c, 8, 1.0, 8, hi, none, lu_acc); }
    if (!std::strcmp(argv[2], "t8")) { JointGate::Choice c; c.src = 1; c.t = 8; c.d = 7; g.observe(c, 7, 1.0, 7, hi, none, lu_acc); std::printf("%g\n", g.cost_pred(8,0,0)); }
    std::puts("done");
}
