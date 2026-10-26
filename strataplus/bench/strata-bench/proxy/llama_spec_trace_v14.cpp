#include <cmath>
#include <map>
#include <sstream>
// llama_spec_trace_v14.cpp - v13 + (i) mtp_process null senza contesto MTP (ERRATA_2 holdout_lookup_v12: il v11-v13 cronometrava
// un if su spec==nullptr) + (ii) --live-src aprime|default_a: arbitro proxy/strata_arbiter_v1.hpp (copia di DraftPolicy::choose + gate
// generate.cpp L16536-16568 di Strata 7dd5cf1, s(T) fisso), con entrambi i candidati registrati a ogni round. v13 = committed/accepted limitati al primo EOG del round (errata holdout_lookup_v12, 25/10 08:00 CET). v12: copia di llama_spec_trace.cpp (v11, invariato) + campo "raw" (agent_v12: prompt gia' templato, tokenizzato
// cosi' com'e', nessun concatenamento turn>0) + vmrss/vmhwm nel request row. strata-plus, PROXY CPU. Derived from llama.cpp examples/speculative-simple (MIT) @ d327bf1f.
// Local tool, never pushed. Modes:
//   --mode base : target only, one token per forward (greedy reference y)
//   --mode live : llama.cpp draft-mtp exactly as speculative-simple (live run, gate V1), every round logged
//   --mode tf   : teacher-forced: at EVERY position the MTP drafts Dmax tokens (logged), the target verifies only
//                 id_last (so the committed sequence is y by construction) -> one round row per position (piano.md §6 rule 4)
// In every round the Strata SuffixDrafter (strata-src/src/spec/suffix_drafter.cpp, linked) proposes up to Dmax lookup
// tokens on prompt+committed: logged as cand.lookup. Counterfactual acceptance vs y is added by tools/annotate.py.
// Requires the local patch patches/llamacpp-draft-mtp-probs.patch (draft probabilities: result_p).
#include "arg.h"
#include "common.h"
#include "sampling.h"
#include "speculative.h"
#include "log.h"
#include "llama.h"
#include "strata/spec/suffix_drafter.hpp"
#include "strata_arbiter_v1.hpp"

#include <algorithm>
#include <chrono>
#include <clocale>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;
static double ms_since(Clock::time_point t) { return std::chrono::duration<double, std::milli>(Clock::now() - t).count(); }

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
static long procstat(const char* key) {   // /proc/self/status in kB
    std::ifstream f("/proc/self/status"); std::string l;
    while (std::getline(f, l)) if (l.rfind(key, 0) == 0) return std::atol(l.c_str() + std::strlen(key));
    return -1;
}
static void jtoks(FILE* f, const std::vector<llama_token>& v, size_t n) {
    std::fputc('[', f);
    for (size_t i = 0; i < n && i < v.size(); ++i) std::fprintf(f, "%s%d", i ? "," : "", v[i]);
    std::fputc(']', f);
}

int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");
    // our own args first (removed from argv before common_params_parse)
    std::string prompts, out, mode = "live", tag = "run", dataset_note, live_src = "mtp", ref_path;
    int limit = 0, dmax = 7, reps = 1, p4_reps = 20, p4_tmax = -1, p4_dmax = -1;
    std::string arb_s;   // --arb-s s1,..,s8 (costo fisso per riga, default kShape)
    std::vector<int> p4_tlist;   // --p4-tlist 1,6,7,8,9,10: verify-only knee run (no MTP draft, no lookup), rotated order per rep
    std::vector<char*> rest{argv[0]};
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--prompts") prompts = argv[++i];
        else if (a == "--out") out = argv[++i];
        else if (a == "--mode") mode = argv[++i];
        else if (a == "--tag") tag = argv[++i];
        else if (a == "--limit") limit = std::atoi(argv[++i]);
        else if (a == "--dmax") dmax = std::atoi(argv[++i]);
        else if (a == "--reps") reps = std::atoi(argv[++i]);
        else if (a == "--live-src") live_src = argv[++i];
        else if (a == "--p4-reps") p4_reps = std::atoi(argv[++i]);
        else if (a == "--p4-tmax") p4_tmax = std::atoi(argv[++i]);
        else if (a == "--p4-dmax") p4_dmax = std::atoi(argv[++i]);
        else if (a == "--p4-tlist") { std::string v = argv[++i]; size_t q = 0; while (q < v.size()) { size_t e = v.find(',', q); if (e == std::string::npos) e = v.size(); p4_tlist.push_back(std::atoi(v.substr(q, e - q).c_str())); q = e + 1; } }
        else if (a == "--ref") ref_path = argv[++i];
        else if (a == "--arb-s") arb_s = argv[++i];
        else rest.push_back(argv[i]);
    }
    std::string flags;
    for (size_t i = 1; i < rest.size(); ++i) { flags += rest[i]; flags += ' '; }
    int rargc = (int) rest.size();
    common_params params;
    common_init();
    if (!common_params_parse(rargc, rest.data(), params, LLAMA_EXAMPLE_SPECULATIVE)) return 1;
    const bool tf = mode == "tf";
    // diagnostics (greedy-equality check): draft = the reference greedy output y (yright: always accepted, T=dmax+1)
    // or y with every token shifted by one id (ywrong: always rejected, T=dmax+1, full rollback every round)
    const bool ydiag = mode == "live" && (live_src == "yright" || live_src == "ywrong");
    const bool lookup_only = mode == "live" && (live_src == "lookup" || ydiag);
    std::map<std::string, std::vector<llama_token>> ref;
    if (!ref_path.empty()) {
        std::ifstream f(ref_path); std::string l;
        while (std::getline(f, l)) {
            const size_t t = l.find('\t'); if (t == std::string::npos) continue;
            std::vector<llama_token> v; std::stringstream ss(l.substr(t + 1)); std::string x;
            while (std::getline(ss, x, ',')) if (!x.empty()) v.push_back(std::atoi(x.c_str()));
            ref[l.substr(0, t)] = v;
        }
    }
    const bool combo = mode == "live" && live_src == "combo";
    // v14: arms with the Strata-like arbiter. aprime = --spec 8 --mtp-max-t 4 (S=8, S_mtp=4, min_p 0);
    // default_a = --spec 4 --spec-min-p 0.5 -> S=6, S_mtp=4 (generate.cpp L3208-3210), min_p 0.5
    const bool arb = mode == "live" && (live_src == "aprime" || live_src == "default_a");
    const int arb_S = live_src == "default_a" ? 6 : 8, arb_Smtp = 4;
    const double arb_minp = live_src == "default_a" ? 0.5 : 0.0;
    double arb_cost[sparb::kMaxT + 1];
    for (int t = 0; t <= sparb::kMaxT; ++t) arb_cost[t] = sparb::kShape[t];
    if (!arb_s.empty()) { std::stringstream ss(arb_s); std::string x; int t = 1; while (std::getline(ss, x, ',') && t <= sparb::kMaxT) arb_cost[t++] = std::atof(x.c_str()); }
    if (arb && (dmax != 7 || params.speculative.draft.n_max != 3)) { std::fprintf(stderr, "aprime/default_a: richiesti --dmax 7 e --spec-draft-n-max 3\n"); return 1; }
    const bool base = mode == "base" || lookup_only;   // lookup-only: no MTP context at all
    const int mtp_k = tf ? dmax : params.speculative.draft.n_max;   // MTP depth actually drafted per round
    // size the context (n_rs_seq rollback window, outputs) for the longest draft we may verify (lookup up to dmax)
    params.speculative.draft.n_max = std::max(params.speculative.draft.n_max, dmax);
    const auto output_limits = common_speculative_get_output_limits(params.n_batch, params.n_parallel, std::max({common_speculative_n_max(&params.speculative), dmax, p4_tmax - 1, p4_tlist.empty() ? 0 : *std::max_element(p4_tlist.begin(), p4_tlist.end()) - 1}));   // P4 extended grid: up to p4_tmax verify rows
    params.n_outputs_max = output_limits.total;
    params.n_outputs_max_per_seq = output_limits.per_seq;

    llama_backend_init();
    auto llama_init_tgt = common_init_from_params(params);
    llama_model * model_tgt = llama_init_tgt->model();
    llama_context * ctx_tgt = llama_init_tgt->context();
    const llama_vocab * vocab = llama_model_get_vocab(model_tgt);
    common_speculative_init_result_ptr spec_init;
    llama_context * ctx_dft = nullptr;
    if (!base) {
        common_params params_dft = common_base_params_to_speculative(params);
        spec_init = common_speculative_init_from_params(params_dft, model_tgt, ctx_tgt);
        params.speculative.draft.ctx_tgt = ctx_tgt;
        params.speculative.draft.ctx_dft = spec_init->context();
        ctx_dft = params.speculative.draft.ctx_dft;
    }
    const bool use_ckpt_tgt = common_context_can_seq_rm(ctx_tgt) == COMMON_CONTEXT_SEQ_RM_TYPE_FULL;
    const bool use_ckpt_dft = ctx_dft && common_context_can_seq_rm(ctx_dft) == COMMON_CONTEXT_SEQ_RM_TYPE_FULL;
    std::fprintf(stderr, "use_ckpt_tgt=%d use_ckpt_dft=%d mode=%s\n", (int) use_ckpt_tgt, (int) use_ckpt_dft, mode.c_str());
    if (arb && (use_ckpt_tgt || base)) { std::fprintf(stderr, "aprime/default_a: target con checkpoint o senza MTP non supportato\n"); return 1; }

    struct P { std::string id, cat, src, text, sid, turn, raw; };
    std::vector<P> ps;
    { std::ifstream f(prompts); std::string l; while (std::getline(f, l)) if (!l.empty()) ps.push_back({jget(l, "id"), jget(l, "category"), jget(l, "source"), jget(l, "prompt"), jget(l, "session_id"), jget(l, "turn"), jget(l, "raw")}); }
    if (limit > 0 && (int) ps.size() > limit) ps.resize(limit);
    FILE * fo = std::fopen((out + ".jsonl").c_str(), "w");
    if (!fo) return 1;

    long n_g9_violations = 0;
    for (int rep = 0; rep < reps; ++rep) {
    std::map<std::string, std::vector<llama_token>> sess_ctx;   // session_id -> previous turn's prompt + output (y)
    for (const P & pr : ps) {
        const int turn = pr.turn.empty() ? 0 : std::atoi(pr.turn.c_str());
        std::vector<llama_token> inp;
        if (pr.raw == "1") {
            inp = common_tokenize(ctx_tgt, pr.text, true, true);   // gia' templato: add_special come llama-tokenize, parse_special
        } else if (!pr.sid.empty() && turn > 0) {
            // multi-turn: prompt = previous turn's prompt + previous output (the reference y via --ref when given, else our own)
            auto it = sess_ctx.find(pr.sid);
            if (it == sess_ctx.end()) { std::fprintf(stderr, "skip %s: previous turn missing\n", pr.id.c_str()); continue; }
            inp = it->second;
            const bool ended = !inp.empty() && llama_vocab_is_eog(vocab, inp.back());
            const std::string cont = std::string(ended ? "" : "<|im_end|>") + "\n<|im_start|>user\n" + pr.text + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";
            const auto ct = common_tokenize(ctx_tgt, cont, false, true);
            inp.insert(inp.end(), ct.begin(), ct.end());
        } else {
            const std::string chat = "<|im_start|>user\n" + pr.text + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";
            inp = common_tokenize(ctx_tgt, chat, true, true);
        }
        if ((int) inp.size() + params.n_predict + dmax + 4 > (int) llama_n_ctx(ctx_tgt) || llama_n_batch(ctx_tgt) < (uint32_t) inp.size()) {
            std::fprintf(stderr, "skip %s: prompt %zu tokens\n", pr.id.c_str(), inp.size());
            continue;
        }
        llama_memory_clear(llama_get_memory(ctx_tgt), true);
        if (ctx_dft) llama_memory_clear(llama_get_memory(ctx_dft), true);
        const llama_seq_id seq_id = 0;
        common_sampler_ptr smpl(common_sampler_init(model_tgt, params.sampling));
        common_speculative * spec = nullptr;
        if (!base) {
            spec = common_speculative_init(params.speculative, 1);
            if (!spec) { std::fprintf(stderr, "spec init failed\n"); return 1; }
        }
        strata::spec::SuffixDrafter sfx(3, 64);   // same as strata generate (generate.cpp:16428), G3
        sparb::Arbiter arbiter(arb_S, arb_cost);   // v14: reset a ogni prompt (CLI: policy locale al processo, generate.cpp L16429)
        std::string arb_json;
        sfx.append(inp.data(), inp.size());
        std::vector<int32_t> lbuf((size_t) dmax);
        const auto t_enc = Clock::now();
        {
            common_batch batch_prompt(ctx_tgt);
            for (size_t i = 0; i + 1 < inp.size(); ++i) batch_prompt.add(inp[i], i, seq_id, false);
            llama_process(ctx_tgt, LLAMA_PROCESS_TYPE_DECODE, batch_prompt.get());
            if (spec && !common_speculative_process(spec, batch_prompt)) { std::fprintf(stderr, "spec prompt failed\n"); return 1; }
        }
        const double prefill_ms = ms_since(t_enc);
        if (mode == "p4") {
            const int n0 = (int) inp.size() - 1;
            const int NREP = p4_reps;
            common_prompt_checkpoint pck;   // full rollback via state checkpoint (hybrid GDN memory cannot drop all T rows)
            pck.update_pos(n0, llama_memory_seq_pos_min(llama_get_memory(ctx_tgt), seq_id), llama_memory_seq_pos_max(llama_get_memory(ctx_tgt), seq_id));
            pck.update_tgt(ctx_tgt, seq_id, LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY);
            double p4_proc_ms = 0;
            auto fwd = [&](int T) {
                common_batch b(ctx_tgt);
                for (int i = 0; i < T; ++i) b.add(inp[(size_t) i % inp.size()], n0 + i, seq_id, true);
                const auto t0 = Clock::now();
                llama_process(ctx_tgt, LLAMA_PROCESS_TYPE_DECODE, b.get());
                llama_synchronize(ctx_tgt);
                const double ms = ms_since(t0);
                p4_proc_ms = 0;
                if (spec) {   // MTP head must also process the verified rows (part of a round's MTP cost)
                    const auto t1 = Clock::now();
                    common_speculative_process(spec, b);
                    llama_synchronize(ctx_dft);
                    p4_proc_ms = ms_since(t1);
                    llama_memory_seq_rm(llama_get_memory(ctx_dft), seq_id, n0, -1);
                }
                GGML_ASSERT(pck.load_tgt(ctx_tgt, seq_id, LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY));
                llama_memory_seq_rm(llama_get_memory(ctx_tgt), seq_id, pck.pos_max + 1, -1);
                return ms;
            };
            llama_tokens ptgt(inp.begin(), inp.end() - 1);
            if (spec) common_speculative_begin(spec, seq_id, ptgt);
            auto drf = [&](int d) {
                llama_tokens res; std::vector<float> rp;
                auto & dp = common_speculative_get_draft_params(spec, seq_id);
                dp = { true, d, n0, inp.back(), &ptgt, &res };
                dp.result_p = &rp;
                const auto t0 = Clock::now();
                common_speculative_draft(spec);
                llama_synchronize(ctx_dft);
                const double ms = ms_since(t0);
                llama_memory_seq_rm(llama_get_memory(ctx_dft), seq_id, n0, -1);
                return std::make_pair(ms, (int) res.size());
            };
            const int TM = p4_tmax > 0 ? p4_tmax : dmax + 1, DM = p4_dmax > 0 ? p4_dmax : dmax;   // grid T=1..TM, d=1..DM (d=0: no MTP)
            for (int w = 0; w < 3; ++w) { for (int T = 1; T <= TM; ++T) fwd(T); if (spec) drf(DM); }
            if (!p4_tlist.empty()) {   // knee run: order rotated by rep and reversed on odd reps (interleaved, rules out drift)
                const int L = (int) p4_tlist.size();
                for (int w = 0; w < 3; ++w) for (int T : p4_tlist) fwd(T);
                for (int rr = 0; rr < NREP; ++rr) {
                    for (int j = 0; j < L; ++j) {
                        const int idx = (rr % 2 == 0) ? (j + rr / 2) % L : (L - 1 - j + rr / 2) % L;
                        const int T = p4_tlist[idx];
                        const double fms = fwd(T);
                        std::fprintf(fo, "{\"type\":\"p4\",\"label\":\"proxy CPU, modello denso, non AMD\",\"run_id\":\"%s\",\"req_id\":\"%s\",\"ctx_len\":%d,\"rep\":%d,\"pos\":%d,\"what\":\"verify\",\"T\":%d,\"ms\":%.4f}\n", tag.c_str(), pr.id.c_str(), n0 + 1, rr, j, T, fms);
                    }
                }
                std::fflush(fo);
                std::fprintf(stderr, "[%s] p4knee %s ctx %d done\n", tag.c_str(), pr.id.c_str(), n0 + 1);
                if (spec) common_speculative_free(spec);
                continue;
            }
            for (int rr = 0; rr < NREP; ++rr) {
                for (int j = 0; j < TM; ++j) {
                    const int T = (rr % 2 == 0) ? j + 1 : TM - j;   // alternate ascending/descending order
                    const double fms = fwd(T);
                    std::fprintf(fo, "{\"type\":\"p4\",\"label\":\"proxy CPU, modello denso, non AMD\",\"run_id\":\"%s\",\"req_id\":\"%s\",\"ctx_len\":%d,\"rep\":%d,\"what\":\"verify\",\"T\":%d,\"ms\":%.4f,\"mtp_process_ms\":%.4f}\n", tag.c_str(), pr.id.c_str(), n0 + 1, rr, T, fms, p4_proc_ms);
                }
                if (spec) for (int j = 1; j <= DM; ++j) {
                    const int d = (rr % 2 == 0) ? j : DM + 1 - j;
                    auto pm = drf(d);
                    std::fprintf(fo, "{\"type\":\"p4\",\"label\":\"proxy CPU, modello denso, non AMD\",\"run_id\":\"%s\",\"req_id\":\"%s\",\"ctx_len\":%d,\"rep\":%d,\"what\":\"mtp_draft\",\"depth\":%d,\"got\":%d,\"ms\":%.4f}\n", tag.c_str(), pr.id.c_str(), n0 + 1, rr, d, pm.second, pm.first);
                }
                {   // lookup: Strata SuffixDrafter propose(dmax) on the prompt history, averaged over 1000 calls
                    const auto t0 = Clock::now();
                    volatile int acc = 0;
                    for (int q = 0; q < 1000; ++q) acc += sfx.propose(dmax, lbuf.data());
                    const double ms = ms_since(t0) / 1000.0;
                    const auto t1 = Clock::now();
                    for (int q = 0; q < 1000; ++q) sfx.append(inp[(size_t) q % inp.size()]);
                    const double ms_app = ms_since(t1) / 1000.0;
                    std::fprintf(fo, "{\"type\":\"p4\",\"label\":\"proxy CPU, modello denso, non AMD\",\"run_id\":\"%s\",\"req_id\":\"%s\",\"ctx_len\":%d,\"rep\":%d,\"what\":\"lookup\",\"ms\":%.6f,\"append_ms\":%.6f,\"k\":%d}\n", tag.c_str(), pr.id.c_str(), n0 + 1, rr, ms, ms_app, (int) acc);
                }
            }
            std::fflush(fo);
            std::fprintf(stderr, "[%s] p4 %s ctx %d done\n", tag.c_str(), pr.id.c_str(), n0 + 1);
            if (spec) common_speculative_free(spec);
            continue;
        }
        llama_token id_last = inp.back();
        llama_tokens prompt_tgt(inp.begin(), inp.end() - 1);
        int n_past = (int) inp.size() - 1;
        if (spec) common_speculative_begin(spec, seq_id, prompt_tgt);
        common_batch batch_tgt(ctx_tgt);
        llama_tokens draft, mtp_cand;
        std::vector<float> mtp_p, mtp_pg, mtp_ent;
        common_prompt_checkpoint ckpt;
        std::vector<llama_token> output;
        int n_predict = 0, r = 0;
        bool has_eos = false, replay = false;
        double dec_ms = 0, draft_ms_tot = 0, verify_ms_tot = 0, proc_ms_tot = 0;
        int n_verify = 0, n_drafted = 0, n_accept = 0, n_replay = 0;
        const auto t_dec = Clock::now();
        while (true) {
            double draft_ms = 0, lookup_ms = 0;
            replay = !draft.empty();
            std::string src_used = "mtp";
            arb_json.clear();
            sparb::Decision dec;
            // lookup candidate (Strata SuffixDrafter) on prompt + committed, every round
            int lk = 0, lmatch = 0;
            if (!replay) {
                const auto tl = Clock::now();
                lk = sfx.propose(dmax, lbuf.data());
                lmatch = sfx.last_match();
                lookup_ms = ms_since(tl);
            }
            if (!replay) {
                mtp_cand.clear(); mtp_p.clear();
                if (spec) {
                    ckpt.update_pos(prompt_tgt.size(), llama_memory_seq_pos_min(llama_get_memory(ctx_tgt), seq_id),
                                    llama_memory_seq_pos_max(llama_get_memory(ctx_tgt), seq_id));
                    if (use_ckpt_dft) ckpt.update_dft(ctx_dft, seq_id, LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY);
                    int n_draft_max = (int) llama_n_ctx(ctx_tgt) - n_past - 2;
                    if (!tf && params.n_predict >= 0) n_draft_max = std::min(n_draft_max, params.n_predict - n_predict - 1);
                    n_draft_max = std::max(n_draft_max, 0);
                    mtp_pg.clear(); mtp_ent.clear();
                    // G9 fix: live cap = min(k, tokens left); 0 => no draft call at all (n_max=0 means "no cap" in llama.cpp)
                    const int cap = tf ? mtp_k : std::min(n_draft_max, mtp_k);
                    if (cap > 0) {
                        auto & dp = common_speculative_get_draft_params(spec, seq_id);
                        dp = { true, cap, n_past, id_last, &prompt_tgt, &mtp_cand };
                        dp.result_p = &mtp_p; dp.result_pg = &mtp_pg; dp.result_ent = &mtp_ent;
                        const auto td = Clock::now();
                        common_speculative_draft(spec);
                        draft_ms = ms_since(td);
                    }
                    if ((int) mtp_cand.size() > cap) { ++n_g9_violations; mtp_cand.resize(cap); mtp_p.resize(std::min(mtp_p.size(), (size_t) cap)); mtp_pg.resize(std::min(mtp_pg.size(), (size_t) cap)); mtp_ent.resize(std::min(mtp_ent.size(), (size_t) cap)); }
                    if (!tf) draft = mtp_cand;   // live: verify the MTP draft; tf: verify nothing
                    if (!draft.empty() && use_ckpt_tgt) ckpt.update_tgt(ctx_tgt, seq_id, LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY);
                    if (use_ckpt_dft) GGML_ASSERT(ckpt.load_dft(ctx_dft, seq_id, LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY));
                    llama_memory_seq_rm(llama_get_memory(ctx_dft), seq_id, ckpt.pos_max + 1, -1);
                    if (combo && lk > 0 && !mtp_cand.empty() && lbuf[0] == mtp_cand[0] && lk > (int) mtp_cand.size()) {
                        // Strata-like rule (strata-src generate.cpp:16556-16563): suffix only if it agrees with the head's 1st token
                        draft.assign(lbuf.begin(), lbuf.begin() + std::min(lk, n_draft_max));
                        src_used = "lookup";
                    }
                    if (arb) {
                        // v14 arbiter (proxy/strata_arbiter_v1.hpp). room = 1 + n_draft_max (proxy: ctx e token rimasti, G9).
                        // first_window (generate.cpp L16551, native pack): r==0 -> T=1, nessuna choose, nessuna observe (L16585).
                        const bool fw = r == 0;
                        const int k_used = std::min(lk, arb_S - 1);   // propose(S-1): prefisso di propose(7) (suffix_drafter.cpp L64-86)
                        if (fw) { dec = sparb::Decision{}; dec.T = 1; dec.t_mtp = 1; }
                        else dec = sparb::decide(arbiter, arb_S, arb_Smtp, arb_minp, mtp_pg.data(), (int) mtp_pg.size(), k_used, lmatch,
                                                 lk > 0 ? lbuf[0] : -1, mtp_cand.empty() ? -2 : mtp_cand[0], 1 + n_draft_max);
                        const int nd = dec.T - 1;
                        if (dec.lookup) { draft.assign(lbuf.begin(), lbuf.begin() + std::min(nd, lk)); src_used = "lookup"; }
                        else { draft.assign(mtp_cand.begin(), mtp_cand.begin() + std::min(nd, (int) mtp_cand.size())); src_used = "mtp"; }
                        char ab[640];
                        std::snprintf(ab, sizeof ab, ",\"arbiter\":{\"impl\":\"strata_arbiter_v1\",\"arm\":\"%s\",\"S\":%d,\"S_mtp\":%d,\"spec_min_p\":%.2f,\"first_window\":%s,"
                                      "\"k_full\":%d,\"k_used\":%d,\"match\":%d,\"t_mtp\":%d,\"gate\":%s,\"choose_called\":%s,\"lookup\":%s,\"T_pre_room\":%d,\"room\":%d,\"T\":%d,"
                                      "\"q\":%.6f,\"mtp_tokens_tmtp\":%.6f,\"rounds_before\":%.0f,\"observed\":%s}",
                                      live_src.c_str(), arb_S, arb_Smtp, arb_minp, fw ? "true" : "false", lk, k_used, lmatch, dec.t_mtp,
                                      dec.gate ? "true" : "false", dec.choose_called ? "true" : "false", dec.lookup ? "true" : "false",
                                      dec.T_pre_room, 1 + n_draft_max, dec.T, arbiter.lookup_rate(lmatch), arbiter.mtp_tokens(std::max(1, dec.t_mtp)),
                                      arbiter.rounds(), fw ? "false" : "true");
                        arb_json = ab;
                    }
                } else if (lookup_only) {
                    int n_draft_max = (int) llama_n_ctx(ctx_tgt) - n_past - 2;
                    if (params.n_predict >= 0) n_draft_max = std::min(n_draft_max, params.n_predict - n_predict - 1);
                    n_draft_max = std::max(n_draft_max, 0);
                    draft.assign(lbuf.begin(), lbuf.begin() + std::min(lk, n_draft_max));
                    src_used = "lookup";
                    if (ydiag) {
                        const auto & y = ref.at(pr.id);
                        draft.clear();
                        for (int i = 0; i < std::min(dmax, n_draft_max) && output.size() + i < y.size(); ++i)
                            draft.push_back(live_src == "yright" ? y[output.size() + i] : (y[output.size() + i] + 1) % llama_vocab_n_tokens(vocab));
                        src_used = live_src;
                    }
                    if (use_ckpt_tgt) GGML_ASSERT(false && "lookup-only with checkpointed target not implemented");
                } else if (use_ckpt_tgt) {
                    ckpt.update_pos(prompt_tgt.size(), llama_memory_seq_pos_min(llama_get_memory(ctx_tgt), seq_id),
                                    llama_memory_seq_pos_max(llama_get_memory(ctx_tgt), seq_id));
                }
            }
            const int pos = n_past;
            const auto tv = Clock::now();
            batch_tgt.clear();
            batch_tgt.add(id_last, n_past++, seq_id, true);
            for (size_t i = 0; i < draft.size(); ++i) batch_tgt.add(draft[i], n_past + i, seq_id, true);
            llama_process(ctx_tgt, LLAMA_PROCESS_TYPE_DECODE, batch_tgt.get());
            const double fwd_ms = ms_since(tv);
            const auto tp = Clock::now();
            if (spec && !common_speculative_process(spec, batch_tgt)) { std::fprintf(stderr, "spec process failed\n"); break; }
            const double proc_ms = spec ? ms_since(tp) : -1.0;   // v14: -1 = nessun contesto MTP (scritto null)
            common_sampler_ptr smpl_save;
            if (use_ckpt_tgt) smpl_save.reset(common_sampler_clone(smpl.get()));
            const size_t n_draft = draft.size();
            const auto ts = Clock::now();
            auto ids = common_sampler_sample_and_accept_n(smpl.get(), ctx_tgt, draft);
            const double verify_ms = fwd_ms + ms_since(ts);
            const bool partial = use_ckpt_tgt && ids.size() - 1 < n_draft;
            // target top1/top2 per verify row (row i predicts output index pos+i): logit gap and full-softmax probs (temp 1)
            std::string vm = "[";
            for (size_t i = 0; i <= n_draft; ++i) {
                const float * lg = llama_get_logits_ith(ctx_tgt, (int32_t) i);
                const int nv = llama_vocab_n_tokens(vocab);
                int a = 0, b = -1;
                for (int v = 1; v < nv; ++v) { if (lg[v] > lg[a]) { b = a; a = v; } else if (b < 0 || lg[v] > lg[b]) b = v; }
                double z = 0; for (int v = 0; v < nv; ++v) z += std::exp((double) lg[v] - lg[a]);
                char buf[160];
                std::snprintf(buf, sizeof buf, "%s[%d,%d,%.5f,%.5f,%.5f]", i ? "," : "", a, b, lg[a] - lg[b], 1.0 / z, std::exp((double) lg[b] - lg[a]) / z);
                vm += buf;
            }
            vm += "]";
            // ---- round row (strataplus.v1) ----
            std::fprintf(fo, "{\"type\":\"round\",\"schema\":\"strataplus.v1.1\",\"label\":\"proxy CPU, non AMD\",\"run_id\":\"%s\",\"req_id\":\"%s\",\"session_id\":%s,\"turn\":%d,\"rep\":%d,\"r\":%d,"
                             "\"pos\":%d,\"gen_index\":%d,\"kv_pos\":%d,\"ctx_len\":%d,\"ctx_bucket\":%d,\"source\":\"%s\",\"k_cap\":%d,\"k_proposed\":%zu,\"T\":%zu,\"proposal\":",
                         tag.c_str(), pr.id.c_str(), pr.sid.empty() ? "null" : ("\"" + pr.sid + "\"").c_str(), turn, rep, r, (int) output.size(), (int) output.size(), pos, pos + 1, pos < 6144 ? 0 : pos < 24576 ? 1 : 2,
                         replay ? "replay" : (n_draft > 0 ? src_used.c_str() : "none"), tf ? 0 : (lookup_only ? dmax : mtp_k), n_draft, n_draft + 1);
            jtoks(fo, draft, draft.size());
            std::fprintf(fo, ",\"cand\":{\"mtp\":{\"tokens\":");
            jtoks(fo, replay ? llama_tokens{} : mtp_cand, (size_t) -1);
            std::fprintf(fo, ",\"probs\":[");   // D11/G2: greedy top-1 prob, full-vocab softmax at temp 1 of the MTP logits
            if (!replay) for (size_t i = 0; i < mtp_pg.size(); ++i) std::fprintf(fo, "%s%.5f", i ? "," : "", mtp_pg[i]);
            std::fprintf(fo, "],\"ent\":[");
            if (!replay) for (size_t i = 0; i < mtp_ent.size(); ++i) std::fprintf(fo, "%s%.4f", i ? "," : "", mtp_ent[i]);
            std::fprintf(fo, "],\"probs_sampler\":[");   // old field: sampler p, softmax renormalised over top_k=10
            if (!replay) for (size_t i = 0; i < mtp_p.size(); ++i) std::fprintf(fo, "%s%.5f", i ? "," : "", mtp_p[i]);
            std::fprintf(fo, "]},\"lookup\":{\"tokens\":");
            std::vector<llama_token> lv(lbuf.begin(), lbuf.begin() + lk);
            jtoks(fo, lv, lv.size());
            // v13: committed/accepted clamped at the first EOG of the round (the output loop below stops there; v11/v12 counted past it)
            size_t n_eos = ids.size();
            for (size_t i = 0; i < ids.size(); ++i) if (llama_vocab_is_eog(vocab, ids[i])) { n_eos = i + 1; break; }
            const size_t acc_c = std::min(ids.size() - 1, n_eos);
            std::fprintf(fo, ",\"match\":%d}},\"accepted\":%zu,\"committed\":%zu,\"committed_raw\":%zu,\"eos_clamped\":%s,\"target_tokens\":", lmatch, acc_c,
                         partial ? (size_t) 0 : n_eos, partial ? (size_t) 0 : ids.size(), (!partial && n_eos < ids.size()) ? "true" : "false");
            jtoks(fo, ids, ids.size());
            std::fprintf(fo, ",\"vmargin\":%s", vm.c_str());
            std::fprintf(fo, ",\"partial_restore\":%s,\"ms_measured\":{\"draft\":%.3f,\"lookup\":%.4f,\"verify\":%.3f,\"mtp_process\":%s}%s,"
                             "\"policy\":\"llamacpp-%s-%s\",\"domain\":\"%s\"}\n",
                         partial ? "true" : "false", draft_ms, lookup_ms, verify_ms, spec ? std::to_string(proc_ms).c_str() : "null", arb_json.c_str(), mode.c_str(), live_src.c_str(), pr.cat.c_str());
            ++r;
            if (replay) ++n_replay; else { ++n_verify; n_drafted += (int) n_draft; n_accept += (int) acc_c; }   // v13: clamped at EOG
            draft_ms_tot += draft_ms; verify_ms_tot += verify_ms; if (spec) proc_ms_tot += proc_ms;
            if (arb && !replay && r > 1) arbiter.observe(dec.lookup, dec.T, (int) acc_c, lmatch);   // v14: generate.cpp L16714, solo !first_window (r-1>0)
            if (partial) {   // recurrent target (Qwen3.5 GDN): restore the checkpoint and re-run the accepted tokens
                draft = std::move(ids);
                GGML_ASSERT(ckpt.load_tgt(ctx_tgt, seq_id, LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY));
                llama_memory_seq_rm(llama_get_memory(ctx_tgt), seq_id, ckpt.pos_max + 1, -1);
                if (ctx_dft) {
                    GGML_ASSERT(ckpt.load_dft(ctx_dft, seq_id, LLAMA_STATE_SEQ_FLAGS_PARTIAL_ONLY));
                    llama_memory_seq_rm(llama_get_memory(ctx_dft), seq_id, ckpt.pos_max + 1, -1);
                }
                prompt_tgt.resize(ckpt.n_tokens);
                smpl = std::move(smpl_save);
                n_past = (int) prompt_tgt.size();
                continue;
            }
            if (spec) common_speculative_accept(spec, seq_id, ids.size() - 1);
            n_past += ids.size() - 1;
            n_predict += ids.size();
            for (size_t i = 0; i < ids.size(); ++i) {
                prompt_tgt.push_back(id_last);
                id_last = ids[i];
                output.push_back(id_last);
                sfx.append(id_last);
                if (llama_vocab_is_eog(vocab, id_last)) { has_eos = true; break; }
            }
            draft.clear();
            llama_memory_seq_rm(llama_get_memory(ctx_tgt), seq_id, n_past, -1);
            if (ctx_dft) llama_memory_seq_rm(llama_get_memory(ctx_dft), seq_id, n_past, -1);
            if ((params.n_predict >= 0 && n_predict >= params.n_predict) || has_eos) break;
        }
        dec_ms = ms_since(t_dec);
        if (params.n_predict >= 0 && (int) output.size() > params.n_predict) output.resize(params.n_predict);
        const char * dkind = tf ? "teacher_forced" : "live";
        const std::vector<llama_token> * refv = (tf || mode == "base") ? &output : (ref.count(pr.id) ? &ref.at(pr.id) : nullptr);
        std::fprintf(fo, "{\"type\":\"request\",\"schema\":\"strataplus.v1.1\",\"label\":\"proxy CPU, non AMD\",\"tracer\":\"llama_spec_trace_v14 (committed clamped at EOG; mtp_process null senza MTP; arbitro strata_arbiter_v1)\",\"data_kind\":\"%s\",\"dmax\":%d,\"pos_semantics\":\"pos = output tokens committed before the round (D4)\",\"sampling\":\"greedy\",\"lookup_max_match\":64,", dkind, dmax);
        std::fprintf(fo, "\"ref_tokens\":");
        if (refv) jtoks(fo, *refv, refv->size()); else std::fprintf(fo, "null");
        std::fprintf(fo, ",\"ref_source\":\"%s\",", tf || mode == "base" ? "own T=1 greedy decode (spec off)" : (refv ? "--ref (base T=1 greedy run)" : "none"));
        std::fprintf(fo, "\"run_id\":\"%s\",\"engine\":\"llamacpp\",\"engine_rev\":\"d327bf1f0780f87b8c01b367b61853b0c291d7c4+strataplus-local-patch\","
                         "\"model\":\"%s\",\"flags\":\"%s--mode %s --live-src %s --dmax %d\",\"dataset\":\"%s\",\"domain\":\"%s\",\"req_id\":\"%s\",\"session_id\":%s,\"turn\":%d,\"rep\":%d,"
                         "\"prompt_tokens\":%zu,\"prompt_ids\":",
                     tag.c_str(), params.model.path.c_str(), flags.c_str(), mode.c_str(), live_src.c_str(), dmax, pr.src.c_str(), pr.cat.c_str(), pr.id.c_str(), pr.sid.empty() ? "null" : ("\"" + pr.sid + "\"").c_str(), turn, rep, inp.size());
        jtoks(fo, inp, inp.size());
        std::fprintf(fo, ",\"output_tokens\":%zu,\"output_ids\":", output.size());
        jtoks(fo, output, output.size());
        std::fprintf(fo, ",\"verify_rounds\":%d,\"replay_rounds\":%d,\"drafted\":%d,\"accepted\":%d,\"prefill_ms\":%.3f,\"decode_ms\":%.3f,"
                         "\"draft_ms\":%.3f,\"verify_ms\":%.3f,\"mtp_process_ms\":%s,\"mtp_ctx\":%s,\"use_ckpt_tgt\":%s,\"raw_prompt\":%s,\"vmrss_kb\":%ld,\"vmhwm_kb\":%ld,\"n_ctx\":%u}\n",
                     n_verify, n_replay, n_drafted, n_accept, prefill_ms, dec_ms, draft_ms_tot, verify_ms_tot, spec ? std::to_string(proc_ms_tot).c_str() : "null", spec ? "true" : "false", use_ckpt_tgt ? "true" : "false", pr.raw == "1" ? "true" : "false", procstat("VmRSS:"), procstat("VmHWM:"), llama_n_ctx(ctx_tgt));
        std::fprintf(fo, "{\"type\":\"request_end\",\"schema\":\"strataplus.v1.1\",\"run_id\":\"%s\",\"req_id\":\"%s\",\"rep\":%d,\"output_tokens\":%zu,\"output_ids\":", tag.c_str(), pr.id.c_str(), rep, output.size());
        jtoks(fo, output, output.size());
        std::fprintf(fo, "}\n");
        std::fflush(fo);
        if (!pr.sid.empty()) {
            std::vector<llama_token> h = inp;
            const std::vector<llama_token> & y = (ref.count(pr.id) && mode != "base") ? ref.at(pr.id) : output;
            h.insert(h.end(), y.begin(), y.end());
            sess_ctx[pr.sid] = h;
        }
        std::fprintf(stderr, "[%s] rep %d %s: %zu tok, %d verify + %d replay rounds, acc %d/%d, decode %.0f ms\n", tag.c_str(), rep,
                     pr.id.c_str(), output.size(), n_verify, n_replay, n_accept, n_drafted, dec_ms);
        if (spec) common_speculative_free(spec);
    }
    }
    std::fprintf(stderr, "g9_violations=%ld\n", n_g9_violations);
    std::fclose(fo);
    llama_backend_free();
    return 0;
}
