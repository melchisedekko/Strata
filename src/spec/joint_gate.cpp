// src/spec/joint_gate.cpp - see include/strata/spec/joint_gate.hpp (Strata+ P5, local draft).
#include "strata/spec/joint_gate.hpp"

#include <algorithm>
#include <cmath>

namespace strata::spec {

namespace {
constexpr double kPB[6] = {0.3, 0.6, 0.8, 0.9, 0.95, 0.99};
constexpr int kMB[4] = {4, 6, 12, 24};
int pbucket(double p) { int b = 0; while (b < 6 && kPB[b] <= p) ++b; return b; }   // searchsorted(side="right")
int mbucket(int m) { int b = 0; while (b < 4 && kMB[b] <= m) ++b; return b; }
void censored(int acc_true, int k_alt, int a, int* obs, bool* fail) {
    const int known = a + 1;
    if (acc_true < std::min(k_alt, known)) { *obs = acc_true; *fail = true; return; }
    *obs = std::min({acc_true, k_alt, known});
    *fail = false;
}
}  // namespace

JointGate::JointGate() : JointGate(Options()) {}

JointGate::JointGate(const Options& o) : o_(o) {
    const double pri[7] = {0.15, 0.45, 0.7, 0.85, 0.92, 0.97, 0.99};
    for (int j = 0; j < kD; ++j) {
        for (int b = 0; b < 7; ++b) { hm_s_[j][b] = pri[b] * 2; hm_f_[j][b] = (1 - pri[b]) * 2; }
        hmm_s_[j] = 1.2; hmm_f_[j] = 0.8;
    }
    for (auto& a : hl_s_) for (auto& b : a) for (auto& c : b) for (double& x : c) x = 1.2;
    for (auto& a : hl_f_) for (auto& b : a) for (auto& c : b) for (double& x : c) x = 0.8;
    for (int t = 0; t < 8; ++t) th_[(size_t) t] = 1.0 + 0.15 * t;
    th_[8] = 0.05; th_[9] = 0.001;
    for (int i = 0; i < 10; ++i) P_[i][i] = 1.0;
    P_[8][8] = 0.01; P_[9][9] = 1e-4;
}

double JointGate::cost_pred(int t, int d, int k) const {
    const double v = th_[(size_t) (t - 1)] + th_[8] * d + th_[9] * k;
    return std::max(1e-3, v) * (scale_ > 0 ? scale_ : 1.0);
}

void JointGate::cost_update(int t, int d, int k, double c) {
    double x[10] = {};
    x[t - 1] = 1; x[8] = d; x[9] = k;
    double xt = 0; for (int i = 0; i < 10; ++i) xt += th_[(size_t) i] * x[i];
    if (!(scale_ > 0)) scale_ = c / std::max(1e-3, xt);
    if (frozen_) return;
    const double y = c / scale_, lam = 0.999;
    double Px[10] = {}, den = lam;
    for (int i = 0; i < 10; ++i) { for (int j = 0; j < 10; ++j) Px[i] += P_[i][j] * x[j]; }
    for (int i = 0; i < 10; ++i) den += x[i] * Px[i];
    double g[10];
    for (int i = 0; i < 10; ++i) g[i] = Px[i] / den;
    for (int i = 0; i < 10; ++i) th_[(size_t) i] += g[i] * (y - xt);
    for (int i = 0; i < 10; ++i)
        for (int j = 0; j < 10; ++j) P_[i][j] = (P_[i][j] - g[i] * Px[j]) / lam;
    for (int t2 = 1; t2 < 8; ++t2) th_[(size_t) t2] = std::max(th_[(size_t) t2], th_[(size_t) t2 - 1]);
}

void JointGate::lu_haz(int s, int match, int ag, double h[kD]) const {
    const int mb = mbucket(match);
    for (int j = 0; j < kD; ++j) {
        const int jb = std::min(j, 2);
        h[j] = hl_s_[s][mb][ag][jb] / (hl_s_[s][mb][ag][jb] + hl_f_[s][mb][ag][jb]);
    }
}

void JointGate::mtp_haz(const float* p, int n, double h[kD]) const {
    for (int j = 0; j < kD; ++j) {
        if (j < n || n > 0) {
            const int b = pbucket((double) p[j < n ? j : n - 1]);
            h[j] = hm_s_[j][b] / (hm_s_[j][b] + hm_f_[j][b]);
        } else {
            h[j] = hmm_s_[j] / (hmm_s_[j] + hmm_f_[j]);
        }
    }
}

int JointGate::expect(const double h[kD], int kmax, double e[kD + 1]) {
    double acc = 1.0, surv = 1.0;
    e[0] = 1.0;
    for (int j = 0; j < kmax; ++j) { surv *= h[j]; acc += surv; e[j + 1] = acc; }
    return kmax + 1;
}

bool JointGate::best_lookup(const Lookup lu[kSrc], int d, bool ag_known, double lam, int rem, double* v, int* s,
                            int* t) const {
    bool any = false;
    for (int si = 0; si < kSrc; ++si) {
        if (!o_.use_src[si] || lu[si].k <= 0) continue;
        const int ag = !ag_known ? 2 : (lu[si].agree >= 1 ? 1 : 0);
        double h[kD], e[kD + 1];
        lu_haz(si, lu[si].match, ag, h);
        const int ne = expect(h, std::min({lu[si].k, o_.tmax - 1, rem, kD}), e);
        for (int k = 1; k < ne; ++k) {
            const double val = e[k] - lam * cost_pred(k + 1, d, klu_);
            if (!any || val > *v) { *v = val; *s = si; *t = k + 1; any = true; }
        }
    }
    return any;
}

bool JointGate::start(const Lookup lu[kSrc], int rem, Choice* out) {
    rem_ = rem;
    klu_ = 0;
    for (int si = 0; si < kSrc; ++si) if (o_.use_src[si]) klu_ += lu[si].k;
    const double lam = lambda();
    const double v0 = 1.0 - lam * cost_pred(1, 0, klu_);
    double vl = 0; int sl = 0, tl = 1;
    const bool bl = best_lookup(lu, 0, false, lam, rem, &vl, &sl, &tl);
    *out = Choice{kNone, 1, 0, klu_};
    if (!o_.mtp || rem <= 0) {
        if (bl && vl > v0) *out = Choice{sl == 0 ? kLookup : kPool, tl, 0, klu_};
        return true;
    }
    double hm[kD], em[kD + 1];
    mtp_haz(nullptr, 0, hm);
    const int ne = expect(hm, std::min(o_.tmax - 1, rem), em);   // tmax - 1 <= kD
    double vm = -1e300;
    for (int k = 1; k < ne; ++k) vm = std::max(vm, em[k] - lam * cost_pred(k + 1, k, klu_));
    if (o_.skip && bl && vl >= vm && vl > v0) {
        *out = Choice{sl == 0 ? kLookup : kPool, tl, 0, klu_};
        return true;
    }
    kmax_ = std::min({kD, o_.tmax - 1, rem});
    return false;
}

bool JointGate::keep(const float* p, const float* ent, int d) {
    if (o_.conf_stop) {
        double H = ent != nullptr ? (double) ent[d - 1] : NAN;
        if (std::isnan(H)) H = -std::log(std::max(1e-6, (double) p[d - 1]));
        return !(1 - std::sqrt(o_.gamma * H) < o_.eta) && d < kmax_;
    }
    if (d >= kmax_) return false;
    const double lam = lambda();
    double h[kD], e[kD + 1];
    mtp_haz(p, d, h);
    expect(h, kmax_, e);
    double now = -1e300, ahead = -1e300;
    for (int k = 0; k <= d; ++k) now = std::max(now, e[k] - lam * cost_pred(k + 1, d, klu_));
    for (int k = d + 1; k <= kmax_; ++k) ahead = std::max(ahead, e[k] - lam * cost_pred(k + 1, k, klu_));
    return ahead > now;
}

JointGate::Choice JointGate::finish(const float* p, int d, const Lookup lu[kSrc]) {
    const double lam = lambda();
    double h[kD], e[kD + 1];
    mtp_haz(p, d, h);
    expect(h, d, e);
    Choice best{kNone, 1, d, klu_};
    double bv = -1e300;
    bool first = true;
    for (int k = 1; k <= d; ++k) {
        const double v = e[k] - lam * cost_pred(k + 1, d, klu_);
        if (first || v > bv) { bv = v; best = Choice{kMtp, k + 1, d, klu_}; first = false; }
    }
    const double vn = 1.0 - lam * cost_pred(1, d, klu_);
    if (first || vn > bv) { bv = vn; best = Choice{kNone, 1, d, klu_}; }
    double vl = 0; int sl = 0, tl = 1;
    if (best_lookup(lu, d, true, lam, rem_, &vl, &sl, &tl) && vl > bv) best = Choice{sl == 0 ? kLookup : kPool, tl, d, klu_};
    return best;
}

void JointGate::observe(const Choice& c, int a, double cost, int mtp_acc, const float* mtp_p, const Lookup lu[kSrc],
                        const int lu_acc[kSrc]) {
    cost_update(c.t, c.d, c.klu, cost);
    lam_n_ = 0.995 * lam_n_ + (a + 1);
    lam_c_ = 0.995 * lam_c_ + cost;
    if (c.d > 0) {
        int obs; bool fail;
        censored(mtp_acc, c.d, a, &obs, &fail);
        for (int j = 0; j < std::min(obs + (fail ? 1 : 0), c.d); ++j) {
            const int b = pbucket((double) mtp_p[j]);
            const bool ok = j < obs;
            hm_s_[j][b] += ok; hm_f_[j][b] += !ok;
            hmm_s_[j] = 0.999 * hmm_s_[j] + ok; hmm_f_[j] = 0.999 * hmm_f_[j] + !ok;
        }
    }
    for (int si = 0; si < kSrc; ++si) {
        if (!o_.use_src[si] || lu[si].k <= 0) continue;
        const int mb = mbucket(lu[si].match);
        int obs; bool fail;
        censored(lu_acc[si], std::min(lu[si].k, kD), a, &obs, &fail);
        int ags[2] = {2, lu[si].agree >= 1 ? 1 : 0};
        const int nag = c.d > 0 ? 2 : 1;
        for (int g = 0; g < nag; ++g)
            for (int j = 0; j < std::min(obs + (fail ? 1 : 0), lu[si].k); ++j) {
                const bool ok = j < obs;
                const int jb = std::min(j, 2);
                hl_s_[si][mb][ags[g]][jb] = 0.998 * hl_s_[si][mb][ags[g]][jb] + ok;
                hl_f_[si][mb][ags[g]][jb] = 0.998 * hl_f_[si][mb][ags[g]][jb] + !ok;
            }
    }
}

}  // namespace strata::spec
