// logit_probe.cpp - Strata Policy arbiter_diag (proxy CPU, non AMD, llama.cpp non Strata). Tool locale, mai pushato.
// Inizializzazione del target identica a proxy/llama_spec_trace_v14.cpp L102-153 (stessi flag, n_max=max(n_max,dmax), output limits,
// contesto MTP creato ma mai usato), poi esegue uno "script" di passi sul target e stampa top1/top2 delle righe richieste.
// Lo stesso codice di stampa del tracer (L413-421): argmax/secondo per scansione lineare, gap in float.
// Script (file --jobs), una riga per passo:
//   J <nome>                    nuovo job: llama_memory_clear(ctx_tgt)
//   P <n> t0..tn-1              prefill posizioni 0..n-1, nessun logit (come L205-207)
//   B <pos> <rec> <n> t0..tn-1  batch con logit su tutte le righe a pos..pos+n-1 (come L396-399); rec=1 -> stampa righe
//   R <pos>                     llama_memory_seq_rm(seq 0, pos, -1) (come L480)
//   W <n> t0..                  token di cui stampare il logit in ogni riga registrata
// Uscita (--out): JSONL {job, step, row, pos, top1, top2, gap, l1, l2, watch:[[tok,logit],..], top5:[[tok,logit],..]}
#include "arg.h"
#include "common.h"
#include "speculative.h"
#include "llama.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>
#include <clocale>
int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");
    std::string jobs, out; int dmax = 7; bool eog = false;
    std::vector<char*> rest{argv[0]};
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--jobs") jobs = argv[++i]; else if (a == "--out") out = argv[++i]; else if (a == "--dmax") dmax = std::atoi(argv[++i]);
        else if (a == "--eog") eog = true; else rest.push_back(argv[i]);
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
    std::fprintf(stderr, "can_seq_rm_full=%d n_threads=%d n_batch=%u n_ubatch=%u\n", (int)(common_context_can_seq_rm(ctx) == COMMON_CONTEXT_SEQ_RM_TYPE_FULL),
                 params.cpuparams.n_threads, llama_n_batch(ctx), llama_n_ubatch(ctx));
    const int nv = llama_vocab_n_tokens(vocab);
    if (eog) { for (int v = 0; v < nv; ++v) if (llama_vocab_is_eog(vocab, v)) std::printf("EOG %d\n", v); return 0; }
    std::ifstream f(jobs); FILE * fo = std::fopen(out.c_str(), "w"); if (!fo) return 1;
    std::string line, job; std::vector<llama_token> watch; int step = 0;
    while (std::getline(f, line)) {
        std::istringstream ss(line); std::string op; ss >> op;
        if (op == "J") { ss >> job; llama_memory_clear(llama_get_memory(ctx), true); watch.clear(); step = 0; continue; }
        if (op == "W") { int n; ss >> n; watch.resize(n); for (auto & t : watch) ss >> t; continue; }
        if (op == "R") { int p; ss >> p; llama_memory_seq_rm(llama_get_memory(ctx), 0, p, -1); continue; }
        if (op == "P") {
            int n; ss >> n; std::vector<llama_token> t(n); for (auto & x : t) ss >> x;
            common_batch b(ctx); for (int i = 0; i < n; ++i) b.add(t[i], i, 0, false);
            if (llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, b.get()) != 0) { std::fprintf(stderr, "prefill fail %s\n", job.c_str()); return 1; }
            ++step; continue;
        }
        if (op == "B") {
            int pos, rec, n; ss >> pos >> rec >> n; std::vector<llama_token> t(n); for (auto & x : t) ss >> x;
            common_batch b(ctx); for (int i = 0; i < n; ++i) b.add(t[i], pos + i, 0, true);
            if (llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, b.get()) != 0) { std::fprintf(stderr, "batch fail %s\n", job.c_str()); return 1; }
            if (rec) for (int i = 0; i < n; ++i) {
                const float * lg = llama_get_logits_ith(ctx, i);
                int a = 0, c = -1;
                for (int v = 1; v < nv; ++v) { if (lg[v] > lg[a]) { c = a; a = v; } else if (c < 0 || lg[v] > lg[c]) c = v; }
                std::fprintf(fo, "{\"job\":\"%s\",\"step\":%d,\"row\":%d,\"pos\":%d,\"top1\":%d,\"top2\":%d,\"gap\":%.6f,\"l1\":%.6f,\"l2\":%.6f,\"watch\":[",
                             job.c_str(), step, i, pos + i, a, c, lg[a] - lg[c], lg[a], lg[c]);
                for (size_t w = 0; w < watch.size(); ++w) std::fprintf(fo, "%s[%d,%.6f]", w ? "," : "", watch[w], lg[watch[w]]);
                std::vector<int> idx(nv); for (int v = 0; v < nv; ++v) idx[v] = v;
                std::partial_sort(idx.begin(), idx.begin() + 5, idx.end(), [&](int x, int y) { return lg[x] > lg[y] || (lg[x] == lg[y] && x < y); });
                std::fprintf(fo, "],\"top5\":[");
                for (int k = 0; k < 5; ++k) std::fprintf(fo, "%s[%d,%.6f]", k ? "," : "", idx[k], lg[idx[k]]);
                std::fprintf(fo, "]}\n");
            }
            ++step; continue;
        }
    }
    std::fclose(fo); llama_backend_free(); return 0;
}
