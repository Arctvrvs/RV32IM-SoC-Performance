#include "rv32im/IFetchStreamModel.hpp"

#include <stdexcept>

namespace rv32im {

IFetchStreamModel::IFetchStreamModel(const IFetchStreamConfig& config)
    : config_(config) {}

void IFetchStreamModel::reset(std::uint32_t reset_pc) {
    stats_ = {};
    next_sequential_pc_ = reset_pc;
}

CacheAccessResult IFetchStreamModel::issue(std::uint32_t pc,
                                           DirectMappedCacheModel& icache,
                                           bool replay,
                                           bool lookahead) {
    auto result = icache.access(pc, false);
    if (icache.config().enabled) {
        ++stats_.issued_accesses;
        if (replay) {
            ++stats_.replay_accesses;
        }
        if (lookahead) {
            ++stats_.lookahead_accesses;
        }
    }
    return result;
}

std::uint32_t IFetchStreamModel::ensure_through(std::uint32_t target_pc,
                                                DirectMappedCacheModel& icache) {
    if (!icache.config().enabled) {
        return 0;
    }
    if ((target_pc & 0x3u) != 0u) {
        throw std::runtime_error("IFetchStreamModel target PC must be word aligned");
    }

    std::uint32_t stalls = 0;

    // Milestone 3B's directed cache workloads are straight-line.  If a later
    // branch redirects behind the already-modeled sequential stream, the cache
    // model can still be extended with an explicit redirect hook in Milestone
    // 3C.  For now, already-fetched PCs require no new request here.
    while (next_sequential_pc_ <= target_pc) {
        const bool lookahead = next_sequential_pc_ != target_pc;
        const auto access = issue(next_sequential_pc_, icache, false, lookahead);
        stalls += access.stall_cycles;
        next_sequential_pc_ += 4u;
    }
    return stalls;
}

std::uint32_t IFetchStreamModel::on_dcache_stall(std::uint32_t retired_pc,
                                                 std::uint32_t dcache_stall_cycles,
                                                 DirectMappedCacheModel& icache) {
    if (!icache.config().enabled || dcache_stall_cycles == 0u) {
        return 0;
    }

    const std::uint32_t held_pc = retired_pc + config_.dcache_hold_ahead_bytes;
    std::uint32_t stalls = ensure_through(held_pc, icache);

    for (std::uint32_t i = 0; i < dcache_stall_cycles; ++i) {
        const auto replay = issue(held_pc, icache, true, false);
        stalls += replay.stall_cycles;
    }
    return stalls;
}


std::uint32_t IFetchStreamModel::on_taken_branch(std::uint32_t branch_pc,
                                                 std::uint32_t target_pc,
                                                 DirectMappedCacheModel& icache) {
    if (!icache.config().enabled) {
        next_sequential_pc_ = target_pc;
        ++stats_.redirect_events;
        return 0;
    }

    // The branch itself has already been fetched by ensure_through(branch_pc).
    // Characterization shows two younger sequential requests escape before the
    // EX-stage redirect. Model them through branch_pc+8, including any real
    // direct-mapped cache misses/conflicts they cause.
    const auto before = stats_.issued_accesses;
    const std::uint32_t wrong_path_end = branch_pc + config_.branch_wrong_path_bytes;
    std::uint32_t stalls = ensure_through(wrong_path_end, icache);
    stats_.wrong_path_accesses += (stats_.issued_accesses - before);
    ++stats_.redirect_events;

    // A redirect is a new IF request stream, not a monotonic retired-PC walk.
    // Resetting the sequential pointer is what makes backward-loop targets and
    // their following instructions access the cache again.
    next_sequential_pc_ = target_pc;
    return stalls;
}

std::uint32_t IFetchStreamModel::on_jump_redirect(std::uint32_t jump_pc,
                                                   std::uint32_t target_pc,
                                                   DirectMappedCacheModel& icache) {
    if (!icache.config().enabled) {
        next_sequential_pc_ = target_pc;
        ++stats_.redirect_events;
        return 0;
    }

    // JAL/JALR use the same EX-stage redirect point measured for conditional
    // branches. The two younger sequential requests are real cache accesses;
    // after that, restart the front end at the architectural target. This is
    // what naturally recreates backward-loop and call/return conflict misses.
    const auto before = stats_.issued_accesses;
    const std::uint32_t wrong_path_end = jump_pc + config_.jump_wrong_path_bytes;
    std::uint32_t stalls = ensure_through(wrong_path_end, icache);
    stats_.wrong_path_accesses += (stats_.issued_accesses - before);
    ++stats_.redirect_events;
    next_sequential_pc_ = target_pc;
    return stalls;
}

std::uint32_t IFetchStreamModel::on_system_drain(std::uint32_t system_pc,
                                                 DirectMappedCacheModel& icache) {
    if (!icache.config().enabled) {
        return 0;
    }

    const std::uint32_t final_fetch_pc = system_pc + config_.system_lookahead_bytes;
    std::uint32_t stalls = ensure_through(final_fetch_pc, icache);

    for (std::uint32_t i = 0; i < config_.system_hold_hits; ++i) {
        const auto replay = issue(final_fetch_pc, icache, true, true);
        stalls += replay.stall_cycles;
    }
    return stalls;
}

} // namespace rv32im
