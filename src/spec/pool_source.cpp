// src/spec/pool_source.cpp - see include/strata/spec/pool_source.hpp (Strata+ P4, local draft).
#include "strata/spec/pool_source.hpp"

#include <algorithm>
#include <cstdlib>
#include <memory>

namespace strata::spec {

// The drafter gets 2x the pool's capacity of room, so it never reaches its own "table full" state before evict().
PoolSource::PoolSource(size_t capacity, int gate, int max_match)
    : capacity_(std::max<size_t>(capacity, 1024)), gate_(std::max(gate, 3)), max_match_(std::max(max_match, gate_)),
      d_(3, max_match_, 2 * capacity_ + 4096) {
    text_.reserve(capacity_ + 1024);
}

void PoolSource::append(const int32_t* tokens, size_t n) {
    if (n == 0) return;
    if (text_.size() + n > capacity_) evict();
    text_.insert(text_.end(), tokens, tokens + n);
    d_.append(tokens, n);
}

void PoolSource::evict() {
    const size_t keep = capacity_ / 2;
    if (text_.size() > keep) text_.erase(text_.begin(), text_.end() - (std::ptrdiff_t) keep);
    d_.reset();
    d_.append(text_.data(), text_.size());
    ++evictions_;
}

int PoolSource::propose(const int32_t* tail, int n_tail, int n_pending, int max_k, int32_t* out, int* match) {
    *match = 0;
    // the pool's own history ends with the current request's committed context (append() saw it), so as for
    // PromptLookupSource only the pending drafts are passed on
    n_pending = std::clamp(n_pending, 0, n_tail);
    const int k = d_.propose_after(tail + (n_tail - n_pending), n_pending, max_k, out);
    if (k <= 0 || d_.last_match() < gate_) return 0;
    *match = d_.last_match();
    return k;
}

bool register_pool_from_env() {
    const char* v = std::getenv("STRATA_LOOKUP_POOL");
    if (v == nullptr || *v == '\0') return false;
    char* end = nullptr;
    const unsigned long long cap = std::strtoull(v, &end, 10);
    int gate = 12;
    if (end != nullptr && *end == ',') gate = std::atoi(end + 1);
    if (cap == 0) return false;
    for (const auto& s : extra_draft_sources())
        if (s && dynamic_cast<const PoolSource*>(s.get()) != nullptr) return true;   // registered once
    extra_draft_sources().push_back(std::make_unique<PoolSource>((size_t) cap, gate));
    return true;
}

}  // namespace strata::spec
