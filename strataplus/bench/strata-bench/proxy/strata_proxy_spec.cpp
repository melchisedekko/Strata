// strata_proxy_spec.cpp - PROXY CPU (non numeri AMD) del loop di speculazione di Strata (src/program/generate.cpp 16532-16719)
// su llama.cpp: il target e' un modello GGUF piccolo, l'MTP di Strata e' sostituito da un drafter GGUF (stesso tokenizer).
// La logica di finestra usa il codice REALE di Strata, linkato da strata-src/src/spec/*.cpp:
//   - strata::spec::SuffixDrafter (--suffix-draft), DraftPolicy::choose/observe (MTP vs lookup),
//   - DraftPolicy::chain/observe_chain + propose_from_sources (--lookup-chain), DraftPolicy::keep_draft/observe_probs (STRATA_SPEC_COST=1),
//   - regola --spec-min-p identica a generate.cpp:16540-16543, aggiustamento delle finestre di generate.cpp:3205-3219.
// Greedy (argmax). Una riga JSONL per round (schema: LOG_SCHEMA.md) + una riga di riepilogo per prompt.
#include "llama.h"
#include "strata/spec/draft_policy.hpp"
#include "strata/spec/draft_source.hpp"
#include "strata/spec/suffix_drafter.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;
static double ms_since(Clock::time_point t) { return std::chrono::duration<double, std::milli>(Clock::now() - t).count(); }

struct Cfg {
    std::string name;
    bool drafter = false;   // MTP stand-in
    int spec = 0;           // --spec (rows); 0 = baseline
    double min_p = 0.0;     // --spec-min-p
    int suffix = 0;         // --suffix-draft
    int chain = 0;          // --lookup-chain
    int chain_min = 3;      // --lookup-chain-min
    bool spec_cost = false; // STRATA_SPEC_COST=1
};

static std::string jesc(const std::string& s) {
    std::string o;
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { o += '\\'; o += (char) c; }
        else if (c < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); o += b; }
        else o += (char) c;
    }
    return o;
}
// minimal JSON string field reader (input JSONL is ours: prepare_datasets.py)
static std::string jget(const std::string& line, const std::string& key) {
    const std::string k = "\"" + key + "\": \"";
    size_t i = line.find(k);
    if (i == std::string::npos) return "";
    i += k.size();
    std::string o;
    for (; i < line.size() && line[i] != '"'; ++i) {
        if (line[i] == '\\' && i + 1 < line.size()) {
            char c = line[++i];
            if (c == 'n') o += '\n'; else if (c == 't') o += '\t'; else if (c == 'r') o += '\r';
            else if (c == 'u') {
                unsigned cp = std::stoul(line.substr(i + 1, 4), nullptr, 16); i += 4;
                if (cp >= 0xD800 && cp <= 0xDBFF && line.compare(i + 1, 2, "\\u") == 0) {
                    unsigned lo = std::stoul(line.substr(i + 3, 4), nullptr, 16); i += 6;
                    cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                }
                if (cp < 0x80) o += (char) cp;
                else if (cp < 0x800) { o += (char) (0xC0 | (cp >> 6)); o += (char) (0x80 | (cp & 0x3F)); }
                else if (cp < 0x10000) { o += (char) (0xE0 | (cp >> 12)); o += (char) (0x80 | ((cp >> 6) & 0x3F)); o += (char) (0x80 | (cp & 0x3F)); }
                else { o += (char) (0xF0 | (cp >> 18)); o += (char) (0x80 | ((cp >> 12) & 0x3F)); o += (char) (0x80 | ((cp >> 6) & 0x3F)); o += (char) (0x80 | (cp & 0x3F)); }
            } else o += c;
        } else o += line[i];
    }
    return o;
}

static int argmax_p(const float* l, int n, float* prob) {
    int b = 0;
    for (int i = 1; i < n; ++i) if (l[i] > l[b]) b = i;
    if (prob) {
        double s = 0; const float m = l[b];
        for (int i = 0; i < n; ++i) s += std::exp((double) (l[i] - m));
        *prob = (float) (1.0 / s);
    }
    return b;
}

struct Model {
    llama_model* m = nullptr; llama_context* c = nullptr; const llama_vocab* v = nullptr; int nv = 0;
    llama_batch b{};
};
static bool g_repack = true; static int g_fa = -1;
static bool load(Model& M, const char* path, int threads, int n_ctx) {
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    mp.use_extra_bufts = g_repack;
    M.m = llama_model_load_from_file(path, mp);
    if (!M.m) return false;
    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = n_ctx; cp.n_batch = 512; cp.n_ubatch = 512; cp.n_threads = threads; cp.n_threads_batch = threads;
    cp.no_perf = true;
    cp.flash_attn_type = (enum llama_flash_attn_type) g_fa;
    M.c = llama_init_from_model(M.m, cp);
    if (!M.c) return false;
    M.v = llama_model_get_vocab(M.m);
    M.nv = llama_vocab_n_tokens(M.v);
    M.b = llama_batch_init(512, 0, 1);
    return true;
}
// decode toks at positions pos0.. ; logits for all rows if all_logits, else last only. returns false on error
static bool run(Model& M, const int32_t* t, int n, int pos0, bool all_logits) {
    for (int off = 0; off < n; off += 512) {
        const int m = std::min(512, n - off);
        M.b.n_tokens = m;
        for (int i = 0; i < m; ++i) {
            M.b.token[i] = t[off + i]; M.b.pos[i] = pos0 + off + i; M.b.n_seq_id[i] = 1; M.b.seq_id[i][0] = 0;
            M.b.logits[i] = all_logits || (off + i == n - 1);
        }
        if (llama_decode(M.c, M.b) != 0) return false;
    }
    return true;
}

int main(int argc, char** argv) {
    std::string target, draft, prompts, out, cfgs = "B,A1,A2,A3,A4,A5", run_tag = "r";
    int threads = 6, max_new = 128, reps = 1, n_ctx = 4096, limit = 0;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto nx = [&]() { return std::string(argv[++i]); };
        if (a == "-m") target = nx(); else if (a == "-md") draft = nx(); else if (a == "--prompts") prompts = nx();
        else if (a == "--out") out = nx(); else if (a == "-t") threads = std::stoi(nx()); else if (a == "-n") max_new = std::stoi(nx());
        else if (a == "--configs") cfgs = nx(); else if (a == "--reps") reps = std::stoi(nx()); else if (a == "--ctx") n_ctx = std::stoi(nx());
        else if (a == "--no-repack") g_repack = false; else if (a == "--fa") g_fa = std::stoi(nx());
        else if (a == "--limit") limit = std::stoi(nx()); else if (a == "--tag") run_tag = nx();
        else { std::fprintf(stderr, "unknown arg %s\n", a.c_str()); return 2; }
    }
    // configuration matrix of PROTOCOL.md (proxy: "drafter" = the MTP stand-in)
    std::vector<Cfg> all = {
        {"B", false, 0, 0.0, 0, 0, 3, false},
        {"A1", true, 4, 0.5, 3, 0, 3, false},    // --spec 4 --spec-min-p 0.5 (suffix-draft 3 default)
        {"A2", true, 4, 0.5, 3, 3, 3, false},    // A1 + --lookup-chain 3
        {"A3", true, 4, 0.5, 3, 0, 3, true},     // A1 + STRATA_SPEC_COST=1
        {"A4", true, 4, 0.5, 0, 0, 3, false},    // MTP(drafter)-only: --suffix-draft 0
        {"A5", false, 4, 0.0, 3, 0, 3, false},   // lookup-only: no draft head, --suffix-draft 3
    };
    std::vector<Cfg> sel;
    { std::stringstream ss(cfgs); std::string s; while (std::getline(ss, s, ',')) for (auto& c : all) if (c.name == s) sel.push_back(c); }

    struct P { std::string id, cat, text; };
    std::vector<P> ps;
    { std::ifstream f(prompts); std::string l; while (std::getline(f, l)) if (!l.empty()) ps.push_back({jget(l, "id"), jget(l, "category"), jget(l, "prompt")}); }
    if (limit > 0 && (int) ps.size() > limit) ps.resize(limit);

    llama_backend_init();
    llama_log_set([](ggml_log_level, const char*, void*) {}, nullptr);
    Model T, D;
    if (!load(T, target.c_str(), threads, n_ctx)) { std::fprintf(stderr, "cannot load target\n"); return 1; }
    if (!draft.empty() && !load(D, draft.c_str(), threads, n_ctx)) { std::fprintf(stderr, "cannot load draft\n"); return 1; }
    FILE* fo = std::fopen((out + ".rounds.jsonl").c_str(), "w");
    FILE* fs = std::fopen((out + ".requests.jsonl").c_str(), "w");
    if (!fo || !fs) return 1;

    // one DraftPolicy + SuffixDrafter per config, kept across prompts (as in a serve process)
    std::vector<std::unique_ptr<strata::spec::DraftPolicy>> pol;
    for (auto& c : sel) {
        int S = c.spec;
        if (c.suffix > 0 && S >= 2) S = std::min(S + 2, 8);
        pol.emplace_back(new strata::spec::DraftPolicy(std::max(S, 1)));
        pol.back()->set_robust(c.spec_cost);
    }

    for (int rep = 0; rep < reps; ++rep)
    for (size_t pi = 0; pi < ps.size(); ++pi) {
        const P& pr = ps[pi];
        const std::string chat = "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n" + pr.text +
                                 "<|im_end|>\n<|im_start|>assistant\n";
        std::vector<int32_t> ptok(chat.size() + 16);
        int np = llama_tokenize(T.v, chat.c_str(), (int) chat.size(), ptok.data(), (int) ptok.size(), false, true);
        if (np < 0) { std::fprintf(stderr, "tokenize failed\n"); return 1; }
        ptok.resize(np);
        // alternation: forward order on even (rep+prompt), reversed on odd -> ABBA-style counterbalancing per prompt
        std::vector<size_t> order(sel.size());
        for (size_t i = 0; i < order.size(); ++i) order[i] = i;
        if ((rep + pi) % 2 == 1) std::reverse(order.begin(), order.end());
        for (size_t slot = 0; slot < order.size(); ++slot) {
            const size_t ci = order[slot];
            const Cfg& c = sel[ci];
            strata::spec::DraftPolicy& policy = *pol[ci];
            const bool use_d = c.drafter && D.m != nullptr;
            // windows (generate.cpp:3205-3219)
            int S = c.spec, S_mtp = c.spec;
            if (c.suffix > 0 && S >= 2) { S_mtp = S; S = std::min(S + 2, 8); }
            if (c.chain > 0 && S >= 2) { const int base = S; S = std::max(base, std::min(std::max(base, S_mtp) + c.chain, 8)); }
            llama_memory_clear(llama_get_memory(T.c), true);
            if (D.c) llama_memory_clear(llama_get_memory(D.c), true);
            // prefill
            const auto tp0 = Clock::now();
            if (!run(T, ptok.data(), np, 0, false)) return 1;
            int32_t x = argmax_p(llama_get_logits_ith(T.c, -1), T.nv, nullptr);
            const double prefill_ms = ms_since(tp0);
            double dprefill_ms = 0;
            int n_d = 0;   // drafter KV: valid prefix length of hist
            std::vector<int32_t> hist(ptok);   // prompt + produced
            if (use_d) {   // drafter prefill of the prompt (its own cost, logged separately)
                const auto t0 = Clock::now();
                if (!run(D, ptok.data(), np, 0, false)) return 1;
                n_d = np;
                dprefill_ms = ms_since(t0);
            }
            std::vector<int32_t> produced{x};
            hist.push_back(x);
            bool eos = llama_vocab_is_eog(T.v, x);
            strata::spec::SuffixDrafter sfx;
            strata::spec::PromptLookupSource lsrc(sfx);
            const bool sfx_on = c.suffix > 0 || c.chain > 0;
            if (sfx_on) sfx.append(hist.data(), hist.size());
            strata::spec::DraftPolicy::ChainState cst;
            int chain_rows = S_mtp;
            int p = np;   // position of x
            int64_t rounds = 0, offered = 0, ok = 0, d_off = 0, d_ok = 0, l_off = 0, l_ok = 0;
            double dec_ms = 0, draft_ms_tot = 0, verify_ms_tot = 0;
            std::vector<int32_t> drafts(8), sbuf(8), cbuf(8), window(8), outv(8), ctail;
            std::vector<float> dprob(8, 0.f);
            const auto tdec = Clock::now();
            while (!eos && (int) produced.size() < max_new) {
                const auto t0 = Clock::now();
                policy.set_context(p);
                // 1) drafter chain (MTP stand-in)
                int n_drafted = 0, n_fed_drafts = 0;
                double draft_ms = 0, lookup_ms = 0;
                std::fill(dprob.begin(), dprob.end(), 0.f);
                if (use_d && c.spec >= 2) {
                    const auto td = Clock::now();
                    if (!run(D, hist.data() + n_d, (int) hist.size() - n_d, n_d, false)) return 1;
                    n_d = (int) hist.size();
                    const int cap = S_mtp - 1;
                    for (int idx = 0; idx < cap; ++idx) {
                        drafts[idx] = argmax_p(llama_get_logits_ith(D.c, -1), D.nv, &dprob[idx]);
                        n_drafted = idx + 1;
                        bool more;
                        if (c.spec_cost) { more = policy.keep_draft(cst, idx, dprob[idx], S_mtp); chain_rows = cst.best_rows; }
                        else more = c.min_p <= 0.0 || dprob[idx] >= (float) c.min_p;   // later drafts cannot enter the window
                        if (!more || idx + 1 >= cap) break;
                        if (!run(D, &drafts[idx], 1, n_d + idx, false)) return 1;
                        n_fed_drafts = idx + 1;
                    }
                    draft_ms = ms_since(td);
                }
                int Tw;
                if (!c.spec || c.spec < 2) Tw = 1;
                else if (use_d && c.spec_cost) Tw = std::clamp(chain_rows, 1, std::min(S_mtp, n_drafted + 1));
                else if (use_d && c.min_p > 0.0) { Tw = 1; while (Tw < S_mtp && Tw - 1 < n_drafted && dprob[Tw - 1] >= (float) c.min_p) ++Tw; }
                else if (use_d) Tw = std::min(S_mtp, n_drafted + 1);
                else Tw = 1;   // PROXY: no draft head -> no MTP rows (generate.cpp would fill them from the oracle, 16594-16595)
                // 2) suffix drafter vs MTP window (generate.cpp:16556-16563)
                bool from_sfx = false;
                int sfx_match = 0, k_sfx = 0;
                if (c.suffix > 0 && c.spec >= 2) {
                    const auto tl = Clock::now();
                    k_sfx = sfx.propose(S - 1, sbuf.data());
                    sfx_match = sfx.last_match();
                    if (k_sfx > 0 && (!use_d || n_drafted == 0 || sbuf[0] == drafts[0])) {
                        const auto pk = policy.choose(Tw, k_sfx, sfx_match);
                        if (pk.lookup) { Tw = pk.t; from_sfx = true; }
                    }
                    lookup_ms += ms_since(tl);
                }
                const int room = std::min(std::max(S, 1), n_ctx - p);
                Tw = std::min(Tw, room);
                // 3) --lookup-chain (generate.cpp:16570-16582)
                int chain_n = 0, cm = 0, csrc = -1;
                if (c.chain > 0 && use_d && !from_sfx && Tw < room) {
                    const auto tl = Clock::now();
                    const std::vector<int32_t>& h = sfx.history();
                    const int keep = std::max(0, std::min((int) h.size(), 64 - (Tw - 1)));
                    ctail.assign(h.end() - keep, h.end());
                    ctail.insert(ctail.end(), drafts.begin(), drafts.begin() + (Tw - 1));
                    chain_n = strata::spec::propose_from_sources(lsrc, ctail.data(), (int) ctail.size(), Tw - 1,
                                                                 std::min(c.chain, room - Tw), c.chain_min, cbuf.data(), &cm, &csrc);
                    if (chain_n > 0) {
                        double p_mtp = 1.0;
                        for (int i = 0; i < Tw - 1; ++i) p_mtp *= dprob[i];
                        chain_n = policy.chain(Tw, p_mtp, chain_n, cm);
                    }
                    lookup_ms += ms_since(tl);
                }
                const int T_mtp = Tw;
                Tw += chain_n;
                window[0] = x;
                for (int i = 1; i < Tw; ++i) window[i] = i >= T_mtp ? cbuf[i - T_mtp] : from_sfx ? sbuf[i - 1] : drafts[i - 1];
                // 4) verify
                const auto tv = Clock::now();
                if (!run(T, window.data(), Tw, p, true)) return 1;
                for (int i = 0; i < Tw; ++i) outv[i] = argmax_p(llama_get_logits_ith(T.c, i), T.nv, nullptr);
                int a = 0;
                while (a < Tw - 1 && window[a + 1] == outv[a]) ++a;
                llama_memory_seq_rm(llama_get_memory(T.c), 0, p + a + 1, -1);
                const double verify_ms = ms_since(tv);
                // 5) commit
                const size_t old_len = hist.size();
                int emitted = 0;
                for (int i = 0; i <= a && (int) produced.size() < max_new && !eos; ++i) {
                    produced.push_back(outv[i]); hist.push_back(outv[i]); ++emitted;
                    if (sfx_on) sfx.append(outv[i]);
                    eos = llama_vocab_is_eog(T.v, outv[i]);
                }
                if (use_d) {   // drafter KV: keep the fed drafts that match the committed tokens
                    int keep = 0;
                    while (keep < n_fed_drafts && old_len + keep < hist.size() && drafts[keep] == hist[old_len + keep]) ++keep;
                    n_d = (int) old_len + keep;
                    llama_memory_seq_rm(llama_get_memory(D.c), 0, n_d, -1);
                }
                const double round_ms = ms_since(t0);
                // per-source accounting
                int kd = 0, ad = 0, kl = 0, al = 0;
                const char* src = "none";
                if (from_sfx) { kl = Tw - 1; al = a; src = "lookup"; }
                else {
                    kd = T_mtp - 1; ad = std::min(a, T_mtp - 1);
                    kl = chain_n; al = std::max(0, a - (T_mtp - 1));
                    src = chain_n > 0 ? (kd > 0 ? "drafter+lookup" : "lookup") : (kd > 0 ? "drafter" : "none");
                }
                // policy feedback (generate.cpp:16713-16715)
                if (c.spec_cost && use_d && !from_sfx) policy.observe_probs(dprob.data(), T_mtp - 1, a);
                if (c.spec >= 2) {
                    if (chain_n == 0) policy.observe(from_sfx, Tw, a, sfx_match, round_ms);
                    else policy.observe_chain(T_mtp, chain_n, a, cm, round_ms);
                }
                std::fprintf(fo, "{\"schema\":\"strata-plus-round/v1\",\"proxy\":\"proxy CPU, non numeri AMD\",\"run\":\"%s\",\"config\":\"%s\","
                                 "\"rep\":%d,\"slot\":%zu,\"prompt_id\":\"%s\",\"domain\":\"%s\",\"round\":%lld,\"position\":%d,\"gen_index\":%zu,"
                                 "\"draft_source\":\"%s\",\"k_proposed\":%d,\"k_accepted\":%d,\"k_proposed_drafter\":%d,\"k_accepted_drafter\":%d,"
                                 "\"k_proposed_lookup\":%d,\"k_accepted_lookup\":%d,\"window_rows\":%d,\"emitted\":%d,\"sfx_k\":%d,\"sfx_match\":%d,"
                                 "\"chain_match\":%d,\"n_drafted\":%d,\"draft_probs\":[",
                             run_tag.c_str(), c.name.c_str(), rep, slot, jesc(pr.id).c_str(), pr.cat.c_str(), (long long) rounds, p,
                             produced.size() - emitted, src, Tw - 1, a, kd, ad, kl, al, Tw, emitted, k_sfx, sfx_match, cm, n_drafted);
                for (int i = 0; i < n_drafted; ++i) std::fprintf(fo, "%s%.4f", i ? "," : "", dprob[i]);
                std::fprintf(fo, "],\"min_p\":%.2f,\"draft_ms\":%.3f,\"lookup_ms\":%.4f,\"verify_ms\":%.3f,\"round_ms\":%.3f}\n",
                             c.min_p, draft_ms, lookup_ms, verify_ms, round_ms);
                ++rounds; offered += Tw - 1; ok += a; d_off += kd; d_ok += ad; l_off += kl; l_ok += al;
                draft_ms_tot += draft_ms; verify_ms_tot += verify_ms;
                x = outv[a];
                p += a + 1;
            }
            dec_ms = ms_since(tdec);
            std::fprintf(fs, "{\"schema\":\"strata-plus-request/v1\",\"proxy\":\"proxy CPU, non numeri AMD\",\"run\":\"%s\",\"config\":\"%s\",\"rep\":%d,"
                             "\"slot\":%zu,\"prompt_id\":\"%s\",\"domain\":\"%s\",\"prompt_tokens\":%d,\"generated\":%zu,\"rounds\":%lld,"
                             "\"drafts_offered\":%lld,\"drafts_accepted\":%lld,\"drafter_offered\":%lld,\"drafter_accepted\":%lld,"
                             "\"lookup_offered\":%lld,\"lookup_accepted\":%lld,\"prefill_ms\":%.3f,\"draft_prefill_ms\":%.3f,\"decode_ms\":%.3f,"
                             "\"draft_ms\":%.3f,\"verify_ms\":%.3f,\"S\":%d,\"S_mtp\":%d,\"threads\":%d,\"output_ids\":[",
                         run_tag.c_str(), c.name.c_str(), rep, slot, jesc(pr.id).c_str(), pr.cat.c_str(), np, produced.size(), (long long) rounds,
                         (long long) offered, (long long) ok, (long long) d_off, (long long) d_ok, (long long) l_off, (long long) l_ok,
                         prefill_ms, dprefill_ms, dec_ms, draft_ms_tot, verify_ms_tot, S, S_mtp, threads);
            for (size_t i = 0; i < produced.size(); ++i) std::fprintf(fs, "%s%d", i ? "," : "", produced[i]);
            std::fprintf(fs, "]}\n");
            std::fflush(fo); std::fflush(fs);
            std::fprintf(stderr, "[%s] rep %d %s %s: %zu tok, %lld rounds, acc %lld/%lld, decode %.0f ms\n", run_tag.c_str(), rep,
                         pr.id.c_str(), c.name.c_str(), produced.size(), (long long) rounds, (long long) ok, (long long) offered, dec_ms);
        }
    }
    std::fclose(fo); std::fclose(fs);
    return 0;
}
