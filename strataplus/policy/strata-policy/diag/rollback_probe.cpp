// rollback_probe.cpp - Strata Policy arbiter_diag, PREREG v2 Parte B (proxy CPU, non AMD, llama.cpp non Strata). Tool locale, mai pushato.
// Inizializzazione del target identica a logit_probe.cpp / proxy/llama_spec_trace_v14.cpp L102-153. Nessuna modifica alla libreria:
// usa solo API pubbliche (llama_process, llama_memory_seq_rm, llama_state_seq_get_data in sola lettura).
// Script (--jobs), una riga per passo:
//   J <nome>                 llama_memory_clear
//   P <n> t..                prefill posizioni 0..n-1, nessun logit
//   B <pos> <n> t..          batch con logit su tutte le righe (come il tracer L396-399), logit non salvati
//   R <pos>                  llama_memory_seq_rm(seq 0, pos, -1); stampa il valore di ritorno
//   S <key>                  salva lo stato seq 0 (llama_state_seq_get_data) sotto key
//   L <key> <pos> <n> t..    come B, salva i logit di tutte le righe sotto key e stampa top1/top2/gap per riga
//   C <label> <k1> <k2>      confronta gli stati salvati (byte e per sezione)
//   D <label> <k1> <k2>      confronta i logit salvati (tutto il vocabolario)
//   F <key>                  libera key
#include "arg.h"
#include "common.h"
#include "speculative.h"
#include "llama.h"
#include "ggml.h"
#include <cstdio>
#include <cstring>
#include <cmath>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <clocale>

struct Blk { std::string cat; int type; size_t off, n_el, el; };
struct Parsed { bool ok = false; std::vector<std::pair<size_t,size_t>> meta; std::vector<Blk> blk; int ext = -1; };

static bool rd(const std::vector<uint8_t> & b, size_t & p, void * dst, size_t n) { if (p + n > b.size()) return false; memcpy(dst, b.data() + p, n); p += n; return true; }
static size_t tsize(int t) { return t == GGML_TYPE_F32 ? 4 : (t == GGML_TYPE_F16 || t == GGML_TYPE_BF16) ? 2 : 1; }

// formato: llama_context::state_seq_get_data (magic+seq_id) poi llama_memory_hybrid::state_write = kv (src/llama-kv-cache.cpp L2076-2360) poi recurrent (src/llama-memory-recurrent.cpp L785-1010)
static bool try_parse(const std::vector<uint8_t> & b, int E, Parsed & P) {
    P = Parsed(); size_t p = 8; uint32_t ns;   // intestazione: io_magic u32 + seq_id i32 (src/llama-context.cpp L3440-3441)
    if (b.size() < 8) return false; P.meta.push_back({0, 8});
    if (!rd(b, p, &ns, 4) || ns == 0 || ns > 64) return false;
    for (uint32_t s = 0; s < ns; ++s) {
        uint32_t cc; if (!rd(b, p, &cc, 4)) return false; if (cc == 0) continue;
        size_t m0 = p;
        for (uint32_t i = 0; i < cc; ++i) { int32_t pos; uint32_t nsq; if (!rd(b, p, &pos, 4) || !rd(b, p, &nsq, 4) || nsq > 64) return false; p += E + 4 * nsq; if (p > b.size()) return false; }
        P.meta.push_back({m0, p - m0});
        uint32_t hdr[4]; size_t h0 = p; if (!rd(b, p, hdr, 16)) return false; P.meta.push_back({h0, 16});
        uint32_t vt = hdr[0], nl = hdr[1]; if (vt > 1 || nl == 0 || nl > 512) return false;
        for (uint32_t l = 0; l < nl; ++l) { int32_t t; uint64_t rs; size_t q = p; if (!rd(b, p, &t, 4) || !rd(b, p, &rs, 8) || t < 0 || t >= GGML_TYPE_COUNT) return false;
            P.meta.push_back({q, 12}); size_t n = cc * rs; if (p + n > b.size()) return false; P.blk.push_back({"kv_k", t, p, n / tsize(t), tsize(t)}); p += n; }
        for (uint32_t l = 0; l < nl; ++l) {
            int32_t t; size_t q = p; if (!rd(b, p, &t, 4) || t < 0 || t >= GGML_TYPE_COUNT) return false;
            size_t n;
            if (!vt) { uint64_t rs; if (!rd(b, p, &rs, 8)) return false; n = cc * rs; }
            else { uint32_t es, ne; if (!rd(b, p, &es, 4) || !rd(b, p, &ne, 4)) return false; n = (size_t) ne * cc * es; }
            P.meta.push_back({q, p - q}); if (p + n > b.size()) return false; P.blk.push_back({"kv_v", t, p, n / tsize(t), tsize(t)}); p += n;
        }
    }
    uint32_t cr; size_t m0 = p; if (!rd(b, p, &cr, 4) || cr == 0 || cr > 64) return false;
    for (uint32_t i = 0; i < cr; ++i) { int32_t pos; uint32_t nsq; if (!rd(b, p, &pos, 4) || !rd(b, p, &nsq, 4) || nsq > 64) return false; p += 4 * nsq; }
    uint32_t st, nl; if (!rd(b, p, &st, 4) || !rd(b, p, &nl, 4) || st != 0) return false;
    P.meta.push_back({m0, p - m0});
    std::vector<Blk> rb;
    while (p < b.size()) { int32_t t; uint64_t rs; size_t q = p; if (!rd(b, p, &t, 4) || !rd(b, p, &rs, 8) || t < 0 || t >= GGML_TYPE_COUNT) return false;
        P.meta.push_back({q, 12}); size_t n = cr * rs; if (p + n > b.size()) return false; rb.push_back({"", t, p, n / tsize(t), tsize(t)}); p += n; }
    if (p != b.size() || rb.empty() || rb.size() % 2) return false;
    for (size_t i = 0; i < rb.size(); ++i) { rb[i].cat = i < rb.size() / 2 ? "conv" : "rec"; P.blk.push_back(rb[i]); }
    P.ok = true; P.ext = E; return true;
}
static Parsed parse(const std::vector<uint8_t> & b) { Parsed P; for (int E : {0, 4, 8, 12, 16, 24}) if (try_parse(b, E, P)) return P; return Parsed(); }
static double val(const uint8_t * p, int t) {
    if (t == GGML_TYPE_F32) { float f; memcpy(&f, p, 4); return f; }
    if (t == GGML_TYPE_F16) { ggml_fp16_t h; memcpy(&h, p, 2); return ggml_fp16_to_fp32(h); }
    if (t == GGML_TYPE_BF16) { uint16_t h; memcpy(&h, p, 2); uint32_t u = (uint32_t) h << 16; float f; memcpy(&f, &u, 4); return f; }
    return *p;
}

int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");
    std::string jobs, out; int dmax = 7;
    std::vector<char*> rest{argv[0]};
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--jobs") jobs = argv[++i]; else if (a == "--out") out = argv[++i]; else if (a == "--dmax") dmax = std::atoi(argv[++i]);
        else rest.push_back(argv[i]);
    }
    common_params params; common_init();
    if (!common_params_parse((int) rest.size(), rest.data(), params, LLAMA_EXAMPLE_SPECULATIVE)) return 1;
    params.speculative.draft.n_max = std::max(params.speculative.draft.n_max, dmax);
    const auto ol = common_speculative_get_output_limits(params.n_batch, params.n_parallel, std::max({common_speculative_n_max(&params.speculative), dmax, 0}));
    params.n_outputs_max = ol.total; params.n_outputs_max_per_seq = ol.per_seq;
    llama_backend_init();
    auto init_tgt = common_init_from_params(params);
    llama_model * model = init_tgt->model(); llama_context * ctx = init_tgt->context();
    const llama_vocab * vocab = llama_model_get_vocab(model);
    common_params pd = common_base_params_to_speculative(params);
    auto spec_init = common_speculative_init_from_params(pd, model, ctx);   // come il tracer (contesto MTP presente, mai usato qui)
    const int nv = llama_vocab_n_tokens(vocab);
    const char * tenv = getenv("GGML_CPU_TILED_MM");
    std::fprintf(stderr, "can_seq_rm_full=%d n_threads=%d n_batch=%u n_ubatch=%u n_rs_seq=%u n_vocab=%d GGML_CPU_TILED_MM=%s\n",
                 (int)(common_context_can_seq_rm(ctx) == COMMON_CONTEXT_SEQ_RM_TYPE_FULL), params.cpuparams.n_threads, llama_n_batch(ctx),
                 llama_n_ubatch(ctx), llama_n_rs_seq(ctx), nv, tenv ? tenv : "(unset)");
    std::ifstream f(jobs); FILE * fo = std::fopen(out.c_str(), "w"); if (!fo) return 1;
    std::fprintf(fo, "{\"op\":\"init\",\"n_rs_seq\":%u,\"n_vocab\":%d,\"n_threads\":%d,\"tiled_env\":\"%s\"}\n", llama_n_rs_seq(ctx), nv, params.cpuparams.n_threads, tenv ? tenv : "unset");
    std::map<std::string, std::vector<uint8_t>> ST; std::map<std::string, std::vector<std::vector<float>>> LG;
    std::string line, job;
    auto run = [&](int pos, const std::vector<llama_token> & t, bool logits) {
        common_batch b(ctx); for (size_t i = 0; i < t.size(); ++i) b.add(t[i], pos + (int) i, 0, logits);
        return llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, b.get());
    };
    while (std::getline(f, line)) {
        std::istringstream ss(line); std::string op; ss >> op;
        if (op == "J") { ss >> job; llama_memory_clear(llama_get_memory(ctx), true); continue; }
        if (op == "R") { int p; ss >> p; bool ok = llama_memory_seq_rm(llama_get_memory(ctx), 0, p, -1);
            std::fprintf(fo, "{\"op\":\"R\",\"job\":\"%s\",\"pos\":%d,\"ok\":%s}\n", job.c_str(), p, ok ? "true" : "false"); continue; }
        if (op == "P" || op == "B" || op == "L") {
            std::string key; int pos = 0, n; if (op == "L") ss >> key; if (op != "P") ss >> pos; ss >> n;
            std::vector<llama_token> t(n); for (auto & x : t) ss >> x;
            if (run(pos, t, op != "P") != 0) { std::fprintf(stderr, "process fail %s %s\n", job.c_str(), line.substr(0, 40).c_str()); return 1; }
            if (op == "L") {
                auto & v = LG[key]; v.assign(n, std::vector<float>(nv));
                std::fprintf(fo, "{\"op\":\"L\",\"job\":\"%s\",\"key\":\"%s\",\"pos\":%d,\"rows\":[", job.c_str(), key.c_str(), pos);
                for (int i = 0; i < n; ++i) {
                    const float * lg = llama_get_logits_ith(ctx, i); memcpy(v[i].data(), lg, sizeof(float) * nv);
                    int a = 0, c = -1;
                    for (int w = 1; w < nv; ++w) { if (lg[w] > lg[a]) { c = a; a = w; } else if (c < 0 || lg[w] > lg[c]) c = w; }
                    std::fprintf(fo, "%s[%d,%d,%.6f,%.6f]", i ? "," : "", a, c, lg[a] - lg[c], lg[a]);
                }
                std::fprintf(fo, "]}\n");
            }
            continue;
        }
        if (op == "S") { std::string key; ss >> key; size_t sz = llama_state_seq_get_size(ctx, 0); auto & v = ST[key]; v.resize(sz);
            size_t w = llama_state_seq_get_data(ctx, v.data(), sz, 0); v.resize(w);
            std::fprintf(fo, "{\"op\":\"S\",\"job\":\"%s\",\"key\":\"%s\",\"bytes\":%zu}\n", job.c_str(), key.c_str(), w); continue; }
        if (op == "W") { std::string key, fn; ss >> key >> fn; auto & v = ST.at(key); FILE * w = std::fopen(fn.c_str(), "wb"); std::fwrite(v.data(), 1, v.size(), w); std::fclose(w); continue; } // debug: dump stato su file
        if (op == "F") { std::string key; ss >> key; ST.erase(key); LG.erase(key); continue; }
        if (op == "C") {
            std::string lab, k1, k2; ss >> lab >> k1 >> k2; auto & A = ST.at(k1); auto & Bv = ST.at(k2);
            bool eq = A.size() == Bv.size() && memcmp(A.data(), Bv.data(), A.size()) == 0;
            std::fprintf(fo, "{\"op\":\"C\",\"label\":\"%s\",\"k1\":\"%s\",\"k2\":\"%s\",\"size1\":%zu,\"size2\":%zu,\"bytes_equal\":%s", lab.c_str(), k1.c_str(), k2.c_str(), A.size(), Bv.size(), eq ? "true" : "false");
            Parsed PA = parse(A), PB = parse(Bv);
            bool same = PA.ok && PB.ok && A.size() == Bv.size() && PA.blk.size() == PB.blk.size();
            std::fprintf(fo, ",\"parsed\":%s,\"ext\":%d", same ? "true" : "false", PA.ext);
            if (same) {
                bool meq = true; for (auto & m : PA.meta) if (memcmp(A.data() + m.first, Bv.data() + m.first, m.second)) meq = false;
                std::fprintf(fo, ",\"meta_equal\":%s,\"sec\":{", meq ? "true" : "false");
                std::map<std::string, std::vector<double>> sec; // n_el, n_diff, max_abs, n_blocks, n_blocks_diff, types
                for (auto & bk : PA.blk) {
                    auto & s = sec[bk.cat]; if (s.empty()) s.assign(5, 0.0);
                    size_t nd = 0; double mx = 0;
                    const uint8_t * pa = A.data() + bk.off, * pb = Bv.data() + bk.off;
                    if (memcmp(pa, pb, bk.n_el * bk.el)) for (size_t i = 0; i < bk.n_el; ++i) {
                        if (memcmp(pa + i * bk.el, pb + i * bk.el, bk.el)) { ++nd; double d = std::fabs(val(pa + i * bk.el, bk.type) - val(pb + i * bk.el, bk.type)); if (!(d <= mx)) mx = d; }
                    }
                    s[0] += bk.n_el; s[1] += nd; s[2] = std::max(s[2], mx); s[3] += 1; s[4] += nd ? 1 : 0;
                }
                bool first = true;
                for (auto & kv : sec) { std::fprintf(fo, "%s\"%s\":[%.0f,%.0f,%.9g,%.0f,%.0f]", first ? "" : ",", kv.first.c_str(), kv.second[0], kv.second[1], kv.second[2], kv.second[3], kv.second[4]); first = false; }
                std::fprintf(fo, "},\"types\":[");
                for (size_t i = 0; i < PA.blk.size(); ++i) std::fprintf(fo, "%s\"%s:%d\"", i ? "," : "", PA.blk[i].cat.c_str(), PA.blk[i].type);
                std::fprintf(fo, "]");
            }
            std::fprintf(fo, "}\n"); continue;
        }
        if (op == "D") {
            std::string lab, k1, k2; ss >> lab >> k1 >> k2; auto & A = LG.at(k1); auto & Bv = LG.at(k2);
            std::fprintf(fo, "{\"op\":\"D\",\"label\":\"%s\",\"k1\":\"%s\",\"k2\":\"%s\",\"rows\":[", lab.c_str(), k1.c_str(), k2.c_str());
            for (size_t r = 0; r < std::min(A.size(), Bv.size()); ++r) {
                const float * a = A[r].data(), * b = Bv[r].data(); double mx = 0; size_t nd = 0;
                int ta = 0, tb = 0, sa = -1, sb = -1;
                for (int w = 0; w < nv; ++w) {
                    if (memcmp(&a[w], &b[w], 4)) { ++nd; double d = std::fabs((double) a[w] - b[w]); if (!(d <= mx)) mx = d; }
                    if (w) { if (a[w] > a[ta]) { sa = ta; ta = w; } else if (sa < 0 || a[w] > a[sa]) sa = w;
                             if (b[w] > b[tb]) { sb = tb; tb = w; } else if (sb < 0 || b[w] > b[sb]) sb = w; }
                }
                // [row, n_diff, max_abs, top1_1, top1_2, margin_1, margin_2, l1_1, l1_2]
                std::fprintf(fo, "%s[%zu,%zu,%.9g,%d,%d,%.6f,%.6f,%.6f,%.6f]", r ? "," : "", r, nd, mx, ta, tb, a[ta] - a[sa], b[tb] - b[sb], a[ta], b[tb]);
            }
            std::fprintf(fo, "]}\n"); continue;
        }
    }
    std::fclose(fo); llama_backend_free(); return 0;
}
