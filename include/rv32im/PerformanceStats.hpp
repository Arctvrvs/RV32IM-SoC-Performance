#pragma once

#include <cstdint>
#include <iomanip>
#include <ostream>

namespace rv32im {

struct PerformanceStats {
    std::uint64_t cycles = 0;
    std::uint64_t retired = 0;

    std::uint64_t alu = 0;
    std::uint64_t branches = 0;
    std::uint64_t branches_taken = 0;
    std::uint64_t loads = 0;
    std::uint64_t stores = 0;
    std::uint64_t mul_div = 0;
    std::uint64_t jumps = 0;

    std::uint64_t base_instruction_cycles = 0;
    std::uint64_t pipeline_fill_drain = 0;
    std::uint64_t stall_load_use = 0;
    std::uint64_t stall_branch_redirect = 0;
    std::uint64_t stall_jump_redirect = 0;
    std::uint64_t stall_divider = 0;
    std::uint64_t stall_icache = 0;
    std::uint64_t stall_dcache = 0;
    std::uint64_t stall_cache_overlap = 0;
    std::uint64_t stall_axi = 0;

    std::uint64_t icache_pipeline_hold_replays = 0;
    std::uint64_t dcache_ifstall_replays = 0;

    std::uint64_t icache_accesses = 0;
    std::uint64_t icache_hits = 0;
    std::uint64_t icache_misses = 0;
    std::uint64_t dcache_accesses = 0;
    std::uint64_t dcache_hits = 0;
    std::uint64_t dcache_misses = 0;
    std::uint64_t dcache_writebacks = 0;
    std::uint64_t axi_read_transactions = 0;
    std::uint64_t axi_write_transactions = 0;

    double cpi() const {
        return retired == 0 ? 0.0 : static_cast<double>(cycles) / static_cast<double>(retired);
    }
    double icache_hit_rate() const {
        return icache_accesses == 0 ? 0.0 : static_cast<double>(icache_hits) / static_cast<double>(icache_accesses);
    }
    double dcache_hit_rate() const {
        return dcache_accesses == 0 ? 0.0 : static_cast<double>(dcache_hits) / static_cast<double>(dcache_accesses);
    }

    void print(std::ostream& os) const {
        os << "\n=== RV32IM model statistics ===\n"
           << "retired                 : " << retired << '\n'
           << "predicted cycles        : " << cycles << '\n'
           << "predicted CPI           : " << std::fixed << std::setprecision(4) << cpi() << '\n'
           << "ALU instructions        : " << alu << '\n'
           << "branches                : " << branches << '\n'
           << "branches taken          : " << branches_taken << '\n'
           << "jumps                   : " << jumps << '\n'
           << "loads                   : " << loads << '\n'
           << "stores                  : " << stores << '\n'
           << "M-extension ops         : " << mul_div << '\n'
           << "\n=== Pipeline performance ===\n"
           << "base instruction cycles : " << base_instruction_cycles << '\n'
           << "pipeline fill/drain      : " << pipeline_fill_drain << '\n'
           << "load-use stalls          : " << stall_load_use << '\n'
           << "taken-branch stalls      : " << stall_branch_redirect << '\n'
           << "JAL/JALR redirect stalls : " << stall_jump_redirect << '\n'
           << "divider stalls           : " << stall_divider << "  (8-stage, II=1 calibrated)\n"
           << "I-cache stalls           : " << stall_icache << '\n'
           << "D-cache stalls           : " << stall_dcache << '\n'
           << "I$/D$ overlap cycles     : " << stall_cache_overlap << '\n'
           << "net cache stall cycles   : " << (stall_icache + stall_dcache - stall_cache_overlap) << '\n'
           << "\n=== Cache hierarchy ===\n"
           << "I-cache accesses         : " << icache_accesses << '\n'
           << "I-cache hits             : " << icache_hits << '\n'
           << "I-cache misses           : " << icache_misses << '\n'
           << "I-cache hit rate         : " << std::setprecision(2) << (100.0 * icache_hit_rate()) << "%\n"
           << "D-cache accesses         : " << dcache_accesses << '\n'
           << "D-cache hits             : " << dcache_hits << '\n'
           << "D-cache misses           : " << dcache_misses << '\n'
           << "D-cache writebacks       : " << dcache_writebacks << '\n'
           << "D-cache hit rate         : " << (100.0 * dcache_hit_rate()) << "%\n"
           << "AXI read transactions    : " << axi_read_transactions << '\n'
           << "AXI write transactions   : " << axi_write_transactions << '\n';
    }
};

} // namespace rv32im
