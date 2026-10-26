// Cross-check harness: drives the real strata::spec::DraftPolicy with an op stream on stdin and prints its answers.
// ops:  R robust(0/1) | X pos | C t_mtp lookup_k match | O lookup t acc match ms | P n p0..p(n-1) acc | K cap n p0..
#include "strata/spec/draft_policy.hpp"
#include <cstdio>
#include <vector>
int main() {
    strata::spec::DraftPolicy pol(6);
    char op;
    while (std::scanf(" %c", &op) == 1) {
        if (op == 'R') { int r; std::scanf("%d", &r); pol.set_robust(r != 0); }
        else if (op == 'X') { long long p; std::scanf("%lld", &p); pol.set_context(p); }
        else if (op == 'C') { int t, k, m; std::scanf("%d %d %d", &t, &k, &m); auto p = pol.choose(t, k, m); std::printf("C %d %d\n", p.lookup ? 1 : 0, p.t); }
        else if (op == 'O') { int l, t, a, m; double ms; std::scanf("%d %d %d %d %lf", &l, &t, &a, &m, &ms); pol.observe(l != 0, t, a, m, ms); }
        else if (op == 'P') { int n, a; std::scanf("%d", &n); std::vector<float> p(n); for (auto& x : p) std::scanf("%f", &x); std::scanf("%d", &a); pol.observe_probs(p.data(), n, a); }
        else if (op == 'K') { int cap, n; std::scanf("%d %d", &cap, &n); std::vector<float> p(n); for (auto& x : p) std::scanf("%f", &x);
            strata::spec::DraftPolicy::ChainState st; int steps = 0;
            for (int i = 0; i < cap - 1; ++i) { steps = i + 1; if (!pol.keep_draft(st, i, p[i], cap)) break; }
            std::printf("K %d %d\n", st.best_rows, steps); }
    }
}
