// strata_arbiter_v1.hpp - strata-plus, PROXY CPU, non AMD. Copia fedele (NON codice Strata eseguito) della scelta per round
// MTP/lookup di Strata @7dd5cf18e68c639a8773e096c5c79f971ea2a9f5 (MIT), per la run live (a') del proxy llama.cpp e per il
// replay di Strata Policy (stesso file, identico). Unica modifica intenzionale: il costo di round s(T) e' FISSO e parametrico
// (vettore s[1..8] passato al costruttore), non l'EMA dei tempi misurati (kCostAlpha=0.1, draft_policy.cpp L14/L158-159).
//
// Fonti (sha256 draft_policy.cpp 890649e3c85891acd8c3e7d6de5908591bc81ef92732ecbe6547008efd61224a,
//        draft_policy.hpp eef7a6ee17753a7c5368b12b5f049c5b325be4bd7844b731803ef4f00b876d92,
//        generate.cpp 12d39e8e6817db694f08af1b52171bce2375c117c669cce8fb82d860c6ed59a2):
//   costanti          draft_policy.cpp L13-25 (kShape, kTokAlpha, kDecay, kPriorQ, kPriorN, kProbes, kStaleRounds)
//   margin_ ("rho")   draft_policy.hpp L29 default 0.03; costruttore senza margin in generate.cpp L16429
//   bucket()          draft_policy.cpp L32-34;  lookup_rate() L36-39;  stale() L116;  mtp_tokens() L118-121
//   choose()          draft_policy.cpp L123-152 (probe L145-150, staleness L141-142, q>=0.85 L142/L147)
//   observe()         draft_policy.cpp L154-173 (qui: il ramo costo conta solo cost_n_/last_, il valore resta s(T) fisso)
//   cost_ms()         draft_policy.cpp L41-53 -> qui s[clamp(t,1,8)] sempre (scelta del Lead: s(T) fisso)
//   contesto          set_context() e' no-op senza set_robust(true) (L76-77; STRATA_SPEC_COST assente, generate.cpp L16447):
//                     un solo bucket di costo (bk_=0), nessun bucket di contesto.
//   gate + finestra   generate.cpp L16536 (T=S_mtp), L16540-16542 (--spec-min-p), L16556-16561 (propose(S-1), gate
//                     k>0 && sbuf[0]==drafts[0], choose), L16567-16568 (T=min(T,room)), L16594 (token della finestra),
//                     L16714 (observe(from_sfx, T, a, sfx_match, round_ms) dopo ogni round temporizzato).
// Stato: un oggetto per prompt (in CLI la policy e' locale al processo, L16429, un processo = un prompt): reset a ogni prompt.
#pragma once
#include <algorithm>
#include <array>

namespace sparb {

constexpr int kMaxT = 8;                 // DraftPolicy::kMaxT (draft_policy.hpp L25)
constexpr int kBuckets = 4;              // draft_policy.hpp L26
constexpr double kShape[kMaxT + 1] = {0.0, 1.0, 1.35, 1.7, 2.05, 2.45, 2.85, 3.25, 3.6};   // L13
constexpr double kTokAlpha = 0.05;       // L15
constexpr double kDecay = 0.97;          // L17
constexpr double kPriorQ[kBuckets] = {0.75, 0.88, 0.93, 0.96};   // L20
constexpr double kPriorN = 4.0;          // L21
constexpr int kProbes = 3;               // L22
constexpr double kStaleRounds = 300.0;   // L25
constexpr double kMargin = 0.03;         // draft_policy.hpp L29

struct Pick { bool lookup = false; int t = 1; };

class Arbiter {
public:
    // s[t], t=1..8: costo relativo fisso di un round di t righe (s[0] ignorato). Scenario base: s = kShape.
    explicit Arbiter(int max_t, const double* s = kShape, double margin = kMargin)
        : max_t_(std::clamp(max_t, 1, kMaxT)), margin_(margin) { for (int t = 0; t <= kMaxT; ++t) s_[t] = s[t]; }

    static int bucket(int match) { return match < 6 ? 0 : match < 12 ? 1 : match < 24 ? 2 : 3; }
    double lookup_rate(int match) const { const int b = bucket(match); return (ok_[b] + kPriorN * kPriorQ[b]) / (ok_[b] + bad_[b] + kPriorN); }
    double cost_ms(int t) const { return s_[std::clamp(t, 1, kMaxT)]; }              // FISSO (differenza voluta)
    bool stale(int t) const { return cost_n_[t] > 0 && rounds_ - last_[t] > kStaleRounds; }
    double mtp_tokens(int t) const { return mtp_n_[t] > 0 ? mtp_tok_[t] : 1.0 + 0.7 * (t - 1); }

    Pick choose(int t_mtp, int lookup_k, int match) const {                           // draft_policy.cpp L123-152
        Pick p;
        p.t = std::clamp(t_mtp, 1, max_t_);
        if (lookup_k <= 0) return p;
        const double base = mtp_tokens(p.t) / cost_ms(p.t);
        const double q = lookup_rate(match);
        double e = 1.0, qi = 1.0, best = 0.0;
        int best_t = 0;
        for (int k = 1; k <= std::min(lookup_k, max_t_ - 1); ++k) {
            qi *= q;
            e += qi;
            const double r = e / cost_ms(k + 1);
            if (r > best) { best = r; best_t = k + 1; }
        }
        const int t_full = std::min(lookup_k, max_t_ - 1) + 1;
        if (best_t > 0 && best > base * (1.0 + margin_)) {
            p.lookup = true;
            p.t = best_t;
            if (best_t < t_full && q >= 0.85 && stale(t_full)) p.t = t_full;
            return p;
        }
        if (t_full > p.t && (cost_n_[t_full] < kProbes || stale(t_full)) && q >= 0.85) {
            p.lookup = true;
            p.t = t_full;
        }
        return p;
    }

    // draft_policy.cpp L154-173 con round_ms > 0 sempre (ogni round temporizzato in Strata ha un tempo > 0):
    // il conteggio/ultimo round della misura avanzano come in L160-161, il valore del costo NON cambia (s fisso).
    void observe(bool lookup, int t, int accepted, int match) {
        t = std::clamp(t, 1, kMaxT);
        cost_n_[t] += 1.0;
        last_[t] = rounds_;
        rounds_ += 1.0;
        if (lookup) {
            const int b = bucket(match);
            ok_[b] = kDecay * ok_[b] + accepted;
            bad_[b] = kDecay * bad_[b] + (accepted < t - 1 ? 1.0 : 0.0);
        } else {
            const double got = accepted + 1.0;
            mtp_tok_[t] = mtp_n_[t] > 0 ? (1.0 - kTokAlpha) * mtp_tok_[t] + kTokAlpha * got : got;
            mtp_n_[t] += 1.0;
        }
    }
    double rounds() const { return rounds_; }
    double cost_n(int t) const { return cost_n_[std::clamp(t, 0, kMaxT)]; }

private:
    int max_t_;
    double margin_;
    double s_[kMaxT + 1];
    std::array<double, kMaxT + 1> cost_n_{}, last_{}, mtp_tok_{}, mtp_n_{};
    std::array<double, kBuckets> ok_{}, bad_{};
    double rounds_ = 0;
};

// Una decisione di round come generate.cpp L16536-16568 (CLI, nessuna --lookup-chain, nessun STRATA_SPEC_COST/T_CYCLE,
// nessuna first_window: il proxy non ha la finestra iniziale T=1 del native pack, L16551).
//   S, S_mtp      : --spec e --mtp-max-t effettivi (a') S=8,S_mtp=4 ; (a) default --spec 4 --spec-min-p 0.5 -> S=6,S_mtp=4 (L3208-3210)
//   mtp_p, n_mtp  : probabilita' dei draft MTP (n_mtp >= S_mtp-1 se disponibili), usate solo se spec_min_p > 0 (L16540-16542)
//   k, match      : k = sfx.propose(S-1, sbuf) (L16557), match = sfx.last_match() (L16558)
//   sbuf0, draft0 : primo token lookup e primo draft MTP (gate L16559)
//   room          : righe massime verificabili (L16567: min(win_cap, max_context - p); nel proxy anche token rimasti, vedi run file)
struct Decision { int T = 1; bool lookup = false; bool gate = false; bool choose_called = false; int T_pre_room = 1; int t_mtp = 1; };
inline Decision decide(const Arbiter& a, int S, int S_mtp, double spec_min_p, const float* mtp_p, int n_mtp,
                       int k, int match, int sbuf0, int draft0, int room) {
    Decision d;
    int T = S_mtp;                                                                   // L16536
    if (spec_min_p > 0.0) {                                                          // L16540-16542
        T = 1;
        while (T < S_mtp && T - 1 < n_mtp && mtp_p[T - 1] >= (float) spec_min_p) ++T;
    }
    d.t_mtp = T;
    if (k > 0 && n_mtp > 0 && sbuf0 == draft0) {                                    // L16556-16559 (suffix_draft=3 > 0)
        d.gate = true; d.choose_called = true;
        const Pick pk = a.choose(T, k, match);                                       // L16560
        if (pk.lookup) { T = pk.t; d.lookup = true; }                                // L16561
    }
    d.T_pre_room = T;
    T = std::min(T, std::max(room, 1));                                              // L16567-16568
    d.T = T;
    (void) S;
    return d;
}

}  // namespace sparb
