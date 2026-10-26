// C ABI over the PRODUCTION strata_spec code (DraftPolicy, SuffixDrafter) so the Python replay can call it via ctypes.
// Built against /workspace/strata-src @ 7dd5cf18 with zig c++ (no system g++ on the box). No logic lives here.
#include "strata/spec/draft_policy.hpp"
#include "strata/spec/suffix_drafter.hpp"
#include <cstdint>
using strata::spec::DraftPolicy;
using strata::spec::SuffixDrafter;
extern "C" {
void* dp_new(int max_t, double margin) { return new DraftPolicy(max_t, margin); }
void dp_free(void* p) { delete (DraftPolicy*) p; }
void dp_set_robust(void* p, int on) { ((DraftPolicy*) p)->set_robust(on != 0); }
void dp_set_context(void* p, long long pos) { ((DraftPolicy*) p)->set_context(pos); }
void dp_seed_costs(void* p, const double* ms, int n, double w, int b) { ((DraftPolicy*) p)->seed_costs(ms, n, w, b); }
int dp_choose(void* p, int t_mtp, int lookup_k, int match) {   // returns t, negative if lookup
    auto r = ((DraftPolicy*) p)->choose(t_mtp, lookup_k, match);
    return r.lookup ? -r.t : r.t;
}
void dp_observe(void* p, int lookup, int t, int acc, int match, double ms) { ((DraftPolicy*) p)->observe(lookup != 0, t, acc, match, ms); }
void dp_observe_probs(void* p, const float* pr, int n, int acc) { ((DraftPolicy*) p)->observe_probs(pr, n, acc); }
double dp_lookup_rate(void* p, int match) { return ((DraftPolicy*) p)->lookup_rate(match); }
double dp_cost_ms(void* p, int t) { return ((DraftPolicy*) p)->cost_ms(t); }
// the STRATA_SPEC_COST chain rule exactly as MtpDrafter::draft calls it (src/core/mtp.cpp:1689-1708);
// returns best_rows, writes the number of drafts computed to *steps
int dp_chain_rows(void* p, const float* pr, int cap, int* steps) {
    DraftPolicy::ChainState st;
    int n = 0;
    const int max_steps = cap - 1;
    for (int i = 0; i < max_steps; ++i) { n = i + 1; if (!((DraftPolicy*) p)->keep_draft(st, i, pr[i], cap)) break; }
    *steps = n < 1 ? 1 : n;
    return st.best_rows;
}
void* sd_new(int min_match, int max_match, unsigned long long cap) { return new SuffixDrafter(min_match, max_match, (size_t) cap); }
void sd_free(void* s) { delete (SuffixDrafter*) s; }
void sd_reset(void* s) { ((SuffixDrafter*) s)->reset(); }
void sd_append(void* s, const int32_t* t, unsigned long long n) { ((SuffixDrafter*) s)->append(t, (size_t) n); }
int sd_propose(void* s, int max_k, int32_t* out) { return ((SuffixDrafter*) s)->propose(max_k, out); }
int sd_last_match(void* s) { return ((SuffixDrafter*) s)->last_match(); }
unsigned long long sd_size(void* s) { return ((SuffixDrafter*) s)->size(); }
// teacher-forced lookup over a whole sequence: history = prefix + y[:i]; for each i writes proposal length,
// match and acceptance LCP(proposal, y[i:]) (one native call per request instead of per token)
void sd_scan(void* s, const int32_t* y, int n, int max_k, int* k_out, int* match_out, int* acc_out, int32_t* tok_out) {
    auto* d = (SuffixDrafter*) s;
    int32_t buf[64];
    for (int i = 0; i < n; ++i) {
        const int k = d->propose(max_k, buf);
        int a = 0;
        while (a < k && i + a < n && buf[a] == y[i + a]) ++a;
        k_out[i] = k; match_out[i] = k > 0 ? d->last_match() : 0; acc_out[i] = a;
        if (tok_out) for (int j = 0; j < max_k; ++j) tok_out[(size_t) i * max_k + j] = j < k ? buf[j] : -1;
        d->append(y[i]);
    }
}
}

// Strata+ P2/P3 entry points (patched DraftPolicy only: patches/P2_deterministic_cost.diff + P3_counterfactual_feedback.diff)
extern "C" {
void dp_observe_counterfactual(void* p, int lookup, int t, int acc, int fail_seen, int match, int n_mtp) {
    (void) n_mtp;
    ((strata::spec::DraftPolicy*) p)->observe_counterfactual(lookup != 0, t, acc, fail_seen != 0, match);
}
void dp_set_frozen_costs(void* p, int on) { ((strata::spec::DraftPolicy*) p)->set_frozen_costs(on != 0); }
}

// Strata+ P5: the joint source+depth gate (patches/P5_joint_gate.diff)
#include "strata/spec/joint_gate.hpp"
using strata::spec::JointGate;
extern "C" {
void* jg_new(int use_lk, int use_pl, int mtp, int skip, int conf_stop, double gamma, double eta, int tmax) {
    JointGate::Options o;
    o.use_src[0] = use_lk != 0; o.use_src[1] = use_pl != 0;
    o.mtp = mtp != 0; o.skip = skip != 0; o.conf_stop = conf_stop != 0; o.gamma = gamma; o.eta = eta; o.tmax = tmax;
    return new JointGate(o);
}
void jg_free(void* g) { delete (JointGate*) g; }
// lu: [lk_k, lk_m, lk_agree, pl_k, pl_m, pl_agree]; p, ent: 7 each (ent may be NaN); out: src, t, d, klu
void jg_act(void* g, int rem, const int* lu, const float* p, const float* ent, int* out) {
    JointGate& G = *(JointGate*) g;
    JointGate::Lookup L[2] = {{lu[0], lu[1], lu[2]}, {lu[3], lu[4], lu[5]}};
    JointGate::Choice c;
    if (!G.start(L, rem, &c)) {
        int d = 0;
        while (true) { ++d; if (!G.keep(p, ent, d)) break; }
        c = G.finish(p, d, L);
    }
    out[0] = c.src; out[1] = c.t; out[2] = c.d; out[3] = c.klu;
}
void jg_observe(void* g, const int* ch, int a, double cost, int mtp_acc, const float* p, const int* lu, const int* lu_acc) {
    JointGate::Lookup L[2] = {{lu[0], lu[1], lu[2]}, {lu[3], lu[4], lu[5]}};
    JointGate::Choice c{ch[0], ch[1], ch[2], ch[3]};
    ((JointGate*) g)->observe(c, a, cost, mtp_acc, p, L, lu_acc);
}
void jg_set_frozen(void* g, int on) { ((JointGate*) g)->set_frozen(on != 0); }
}
