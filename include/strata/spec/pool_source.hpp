// include/strata/spec/pool_source.hpp - Strata+ P4 (local draft, H2): a persistent cross-request lookup pool.
//
// A DraftSource over the committed text of EVERY request this process served (prompts and outputs), not reset
// between requests: a repeat of an earlier request's text (the same file edited again, the same boilerplate, a
// session's previous turns) can be drafted even when the current request has not seen it.  Registered through
// extra_draft_sources() (register_pool_from_env()); the engine asks it beside the request's own text.
//
// Two things the SuffixDrafter alone does not give a persistent pool:
//  - eviction: the drafter stops indexing once its table is full; the pool keeps a copy of its text and, when it
//    reaches `capacity` tokens, rebuilds the drafter from the newest half (the oldest text is forgotten);
//  - a match gate: the pool proposes only on a match of at least `gate` tokens.  The offline replay (E1, replay
//    v2) finds that on independent requests short pool matches are mostly coincidental and cost windows (a
//    regression unless gate >= 12), while on sessions a gate of 6-12 pays.
#pragma once
#include "strata/spec/draft_source.hpp"
#include "strata/spec/suffix_drafter.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace strata::spec {

class PoolSource final : public DraftSource {
public:
    /// `capacity`: tokens kept (the newest; eviction halves).  `gate`: the shortest match proposed on.
    explicit PoolSource(size_t capacity = 1u << 20, int gate = 12, int max_match = 64);
    const char* name() const override { return "pool"; }
    void reset() override {}   // persistent: a new request does not clear the pool
    void append(const int32_t* tokens, size_t n) override;
    int propose(const int32_t* tail, int n_tail, int n_pending, int max_k, int32_t* out, int* match) override;
    size_t size() const { return text_.size(); }
    int gate() const { return gate_; }
    size_t evictions() const { return evictions_; }

private:
    void evict();
    size_t capacity_;
    int gate_, max_match_;
    SuffixDrafter d_;
    std::vector<int32_t> text_;   // what d_ indexes, in order (kept for the rebuild)
    size_t evictions_ = 0;
};

/// STRATA_LOOKUP_POOL=<capacity tokens>[,<gate>] (e.g. 1048576,12): registers one PoolSource with
/// extra_draft_sources().  Call once at startup, before the first request; returns whether a pool was registered.
bool register_pool_from_env();

}  // namespace strata::spec
