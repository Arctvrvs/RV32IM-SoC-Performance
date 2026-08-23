#pragma once

#include "rv32im/CacheModel.hpp"
#include "rv32im/Memory.hpp"
#include "rv32im/IFetchStreamModel.hpp"
#include "rv32im/PerformanceStats.hpp"
#include "rv32im/PipelineTimingModel.hpp"
#include "rv32im/Trace.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

namespace rv32im {

struct CpuConfig {
    std::size_t memory_size = 1024 * 1024;
    std::uint32_t reset_pc = 0;
    std::uint64_t max_instructions = 10'000'000;
    std::string trace_path;

    CacheConfig icache{};
    CacheConfig dcache{};
};

class CpuModel {
public:
    explicit CpuModel(const CpuConfig& config = {});

    void load_program(const std::string& hex_path, std::uint32_t base_addr = 0);
    void load_data(const std::string& hex_path, std::uint32_t base_addr = 0);
    void reset(std::uint32_t pc = 0);

    // Executes one architecturally retired instruction.
    // Returns false after the CPU has halted.
    bool step();
    void run();

    bool halted() const { return halted_; }
    std::uint32_t pc() const { return pc_; }
    std::uint32_t reg(unsigned index) const { return regs_.at(index); }

    const PerformanceStats& stats() const { return stats_; }
    const Memory& memory() const { return data_memory_; }
    Memory& memory() { return data_memory_; }
    const Memory& instruction_memory() const { return instruction_memory_; }

private:
    static std::int32_t sign_extend(std::uint32_t value, unsigned bits);

    void write_reg(unsigned rd, std::uint32_t value, RetireEvent& event);
    bool sequential_next_redirect_target(std::uint32_t next_pc, std::uint32_t& target_pc) const;
    std::uint32_t cache_overlap_credit(std::uint32_t dcache_stall_cycles) const;
    [[noreturn]] void illegal(std::uint32_t insn, const char* reason) const;

    CpuConfig config_;
    Memory instruction_memory_;
    Memory data_memory_;
    std::array<std::uint32_t, 32> regs_{};
    std::uint32_t pc_ = 0;
    bool halted_ = false;
    std::uint64_t cache_overlap_cycles_ = 0;
    std::uint64_t dcache_ifstall_replays_ = 0;
    PerformanceStats stats_{};
    PipelineTimingModel timing_{};
    DirectMappedCacheModel icache_{};
    DirectMappedCacheModel dcache_{};
    IFetchStreamModel ifetch_{};
    TraceWriter trace_;
};

} // namespace rv32im
