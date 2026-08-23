#pragma once

#include "rv32im/CacheModel.hpp"

#include <cstdint>

namespace rv32im {

// Front-end fetch-stream model calibrated from VCS characterization of the
// current in-order 5-stage RTL.  It models cache *requests*, not just retired
// instruction PCs.
//
// Characterized behavior used in Milestone 3B:
//   * normal straight-line execution eventually fetches each retired PC once
//   * when an instruction in MEM stalls on D-cache, IF is three instructions
//     ahead (retired PC + 12) and repeatedly re-requests that held PC once per
//     D-cache stall cycle
//   * ECALL/EBREAK drain allows two younger sequential PCs to be fetched; the
//     second younger PC is then re-requested for two hit cycles while halt
//     reaches WB
//
// The class deliberately owns only front-end request sequencing.  The actual
// direct-mapped hit/miss behavior remains in DirectMappedCacheModel.
struct IFetchStreamConfig {
    std::uint32_t dcache_hold_ahead_bytes = 12;
    std::uint32_t system_lookahead_bytes = 8;
    std::uint32_t system_hold_hits = 2;

    // Conditional branches resolve in EX. Before a taken redirect becomes
    // visible to IF, the two younger sequential PCs have already been
    // requested. Characterized in Milestone 3C.
    std::uint32_t branch_wrong_path_bytes = 8;

    // JAL/JALR also resolve through the EX redirect path in this RTL. Two
    // younger sequential fetch requests escape before the jump target is
    // installed, matching the conditional-branch front-end behavior.
    std::uint32_t jump_wrong_path_bytes = 8;
};

struct IFetchStreamStats {
    std::uint64_t issued_accesses = 0;
    std::uint64_t replay_accesses = 0;
    std::uint64_t lookahead_accesses = 0;
    std::uint64_t redirect_events = 0;
    std::uint64_t wrong_path_accesses = 0;
};

class IFetchStreamModel {
public:
    explicit IFetchStreamModel(const IFetchStreamConfig& config = {});

    void reset(std::uint32_t reset_pc = 0);

    // Ensure the front end has issued sequential requests through target_pc.
    // Returns I-cache stall cycles introduced by misses along that path.
    std::uint32_t ensure_through(std::uint32_t target_pc,
                                 DirectMappedCacheModel& icache);

    // Model the IF behavior while an older data-memory operation stalls MEM.
    // The front end first reaches retired_pc + 12, then repeatedly requests the
    // held PC once per D-cache stall cycle.  Returns any *I-cache* stall cycles
    // required to reach the held PC; replay accesses are expected to hit.
    std::uint32_t on_dcache_stall(std::uint32_t retired_pc,
                                  std::uint32_t dcache_stall_cycles,
                                  DirectMappedCacheModel& icache);

    // Model a taken conditional-branch redirect. The current RTL resolves the
    // branch in EX, so IF requests branch_pc+4 and branch_pc+8 before the
    // redirect takes effect. The next architectural fetch then restarts at
    // target_pc even if that target was fetched previously. Returns I-cache
    // stall cycles caused by those two wrong-path requests.
    std::uint32_t on_taken_branch(std::uint32_t branch_pc,
                                  std::uint32_t target_pc,
                                  DirectMappedCacheModel& icache);

    // Model an unconditional JAL/JALR redirect. VCS characterization shows
    // the same two younger sequential fetch requests as a taken branch, then
    // a fresh target-stream request even for backward/call-return redirects.
    std::uint32_t on_jump_redirect(std::uint32_t jump_pc,
                                   std::uint32_t target_pc,
                                   DirectMappedCacheModel& icache);

    // Model fetches younger than a terminating SYSTEM instruction while it
    // drains to WB. Returns I-cache stall cycles introduced by those lookahead
    // fetches.
    std::uint32_t on_system_drain(std::uint32_t system_pc,
                                  DirectMappedCacheModel& icache);

    const IFetchStreamStats& stats() const { return stats_; }
    std::uint32_t next_sequential_pc() const { return next_sequential_pc_; }

private:
    CacheAccessResult issue(std::uint32_t pc,
                            DirectMappedCacheModel& icache,
                            bool replay,
                            bool lookahead);

    IFetchStreamConfig config_{};
    IFetchStreamStats stats_{};
    std::uint32_t next_sequential_pc_ = 0;
};

} // namespace rv32im
