#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace rv32im {

// Analytical model of the caches used by the RTL project:
//   * direct mapped
//   * one 32-bit word per line
//   * blocking
//   * I-cache: read-only refill
//   * D-cache: write-back + write-allocate
//   * AXI-Lite backing memory with a configurable response latency
//
// The miss-stall formulas mirror the RTL cache/memory FSM structure.  With the
// RTL's LATENCY=3 setting, a clean refill costs 7 held pipeline cycles and a
// dirty-victim D-cache miss costs 13 held cycles (writeback + refill).
struct CacheConfig {
    bool enabled = false;
    std::size_t lines = 64;
    std::uint32_t line_bytes = 4;
    std::uint32_t memory_latency = 3;
    bool write_back = false;
    bool write_allocate = true;
};

struct CacheStats {
    std::uint64_t accesses = 0;
    std::uint64_t hits = 0;
    std::uint64_t misses = 0;
    std::uint64_t writebacks = 0;
    std::uint64_t read_transactions = 0;
    std::uint64_t write_transactions = 0;
    std::uint64_t stall_cycles = 0;
};

struct CacheAccessResult {
    bool hit = false;
    bool miss = false;
    bool writeback = false;
    std::uint32_t stall_cycles = 0;
};

class DirectMappedCacheModel {
public:
    explicit DirectMappedCacheModel(const CacheConfig& config = {});

    void configure(const CacheConfig& config);
    void reset();

    CacheAccessResult access(std::uint32_t byte_addr, bool is_write = false);
    bool would_hit(std::uint32_t byte_addr) const;

    const CacheConfig& config() const { return config_; }
    const CacheStats& stats() const { return stats_; }

    std::uint32_t clean_miss_penalty() const;
    std::uint32_t dirty_miss_penalty() const;

private:
    struct Line {
        bool valid = false;
        bool dirty = false;
        std::uint64_t tag = 0;
    };

    static bool is_power_of_two(std::size_t value);

    CacheConfig config_{};
    CacheStats stats_{};
    std::vector<Line> lines_;
};

} // namespace rv32im
