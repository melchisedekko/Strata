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
