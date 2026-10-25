// include/strata/spec/joint_gate.hpp - Strata+ P5 (local draft, H1+H4): one gate that chooses the draft SOURCE
// (none / MTP / prompt lookup / pool) and the MTP DEPTH together.  C++ port of the replay's GateV2
// (/workspace/strata-policy/replay/strata_sim/sim2.py), kept decision-for-decision identical so the offline replay
// can link it (parity test: replay/tests/test_joint_gate_parity.py).
//
// Per round:
//   start()      - before any MTP draft: if a lookup proposal already beats the best value the MTP could reach
//                  (marginal hazards), take it and skip the MTP draft (lookup-first);
//   keep()       - after each MTP draft j (its top-1 prob, optionally its entropy): draft another one?  The value
//                  test compares the best window available now with the best reachable deeper (inherit-last-bucket
//                  hazards); conf_stop replaces it by the AdaEDL-style stop 1 - sqrt(gamma*H_j) < eta (H4 variant);
//   finish()     - with the drafts known: best of MTP windows 1..d, none, lookup windows (agreement now known);
//   observe()    - full-information, censored feedback: the played round's cost, both sources' drafts scored on
//                  the a+1 committed tokens.
// Objective: Dinkelbach E[a+1] - lambda*C, lambda = decayed tokens/cost of the rounds played.  Cost model: online
// RLS on one-hot(T) + rho_mtp*d + rho_lu*k (optimistic prior, monotone in T); frozen() keeps the seeded table.
// SCOPE: single sequence only (CLI and the --serve GEN loop, where DraftPolicy runs).  The batch path (batch_step /
// BGEN) uses one MTP draft per slot and never calls DraftPolicy or this gate: no effect on parallel > 1 serving.
#pragma once
#include <array>
#include <cstdint>

namespace strata::spec {

class JointGate {
public:
    static constexpr int kD = 7;             // MTP drafts considered (Dmax)
    static constexpr int kSrc = 2;           // 0 = prompt lookup (the request's text), 1 = pool
    struct Options {
        bool use_src[kSrc] = {true, false};
        bool mtp = true, skip = true, conf_stop = false;
        double gamma = 0.5, eta = 0.35;
        int tmax = 8;
    };
    struct Lookup { int k = 0, match = 0, agree = -1; };   // agree: first lookup draft == first MTP draft (-1 unknown)
    enum Src { kNone = 0, kMtp = 1, kLookup = 2, kPool = 3 };
    struct Choice { int src = kNone, t = 1, d = 0, klu = 0; };

    JointGate();
    explicit JointGate(const Options& o);

    /// Round start.  `rem` = tokens still to generate after the next one.  Returns true when a lookup window is taken
    /// without drafting the MTP (`*out` filled), false when the MTP should draft (then keep()/finish()).
    bool start(const Lookup lu[kSrc], int rem, Choice* out);
    /// After the MTP drafted `d` tokens with top-1 probs `p[0..d)` (entropies `ent`, may be null): draft another?
    bool keep(const float* p, const float* ent, int d);
    Choice finish(const float* p, int d, const Lookup lu[kSrc]);
    /// After the round: the window played, its committed tokens (accepted a), its cost, and how many drafts of each
    /// candidate equal the committed tokens (acc_true: the replay knows them; the engine passes the a+1-censored LCP,
    /// which censored() treats identically).
    void observe(const Choice& c, int accepted, double cost, int mtp_acc, const float* mtp_p, const Lookup lu[kSrc],
                 const int lu_acc[kSrc]);
    double lambda() const { return lam_n_ / lam_c_; }
    void set_frozen(bool on) { frozen_ = on; }
    /// Seed the cost model with a measured table (STRATA_SPEC_COST_TABLE): s(T) for T = 1..8 in units of one plain
    /// step, the per-draft MTP cost and the per-token lookup cost in the same units, and the step cost `unit` (e.g. ms)
    /// that converts them to observed costs.  With set_frozen(true) the gate then plans on exactly this table (before,
    /// frozen kept the 1+0.15(T-1) prior scaled by the first sample).  Without frozen the RLS starts from it.
    void seed_costs(const double s_by_t[8], double rho_mtp, double rho_lu, double unit);
    /// `rem` for start(): tokens still allowed after the next one, bounded by max_new AND by the context window (the
    /// engine stops when p + T > max_context; max_context <= 0 = no context bound).  Never negative.
    static int remaining(int max_new, int produced, int max_context, int pos);
    double cost_pred(int t, int d, int k) const;   // t clamped to 1..8
    int tmax() const { return o_.tmax; }

private:
    void lu_haz(int s, int match, int ag, double h[kD]) const;
    void mtp_haz(const float* p, int n, double h[kD]) const;
    static int expect(const double h[kD], int kmax, double e[kD + 1]);
    bool best_lookup(const Lookup lu[kSrc], int d, bool ag_known, double lam, int rem, double* v, int* s, int* t) const;
    void cost_update(int t, int d, int k, double c);

    Options o_;
    double hm_s_[kD][7], hm_f_[kD][7], hmm_s_[kD], hmm_f_[kD];
    double hl_s_[kSrc][5][3][3], hl_f_[kSrc][5][3][3];
    std::array<double, 10> th_{};
    double P_[10][10] = {};
    double scale_ = 0.0;   // 0: not set yet
    std::array<double, 8> n_t_{};   // samples per window size
    bool frozen_ = false;
    double lam_n_ = 1.0, lam_c_ = 1.0;
    // the round in progress
    int rem_ = 0, klu_ = 0, kmax_ = 0;
};

}  // namespace strata::spec
