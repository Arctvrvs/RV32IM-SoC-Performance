#pragma once

#include <cstdint>

namespace rv32im {

struct PipelineTimingConfig {
    std::uint32_t pipeline_depth = 5;
    std::uint32_t load_use_penalty = 1;
    std::uint32_t taken_branch_penalty = 2;
    std::uint32_t jump_redirect_penalty = 2;

    // Calibrated from directed VCS characterization of the RTL divider.
    // The RTL uses an 8-stage fully pipelined DIV/REM unit:
    //   * first op in a contiguous divider burst pays latency - 1 = 7 cycles
    //   * immediately consecutive DIV/DIVU/REM/REMU ops accept one per cycle
    //   * any intervening non-divider instruction ends the burst; the next
    //     divider operation pays the startup latency again.
    std::uint32_t divider_latency = 8;
    std::uint32_t divider_initiation_interval = 1;
};

struct PipelineTimingStats {
    std::uint64_t retired = 0;
    std::uint64_t base_instruction_cycles = 0;
    std::uint64_t pipeline_fill_drain = 0;
    std::uint64_t load_use_stalls = 0;
    std::uint64_t branch_redirect_stalls = 0;
    std::uint64_t jump_redirect_stalls = 0;
    std::uint64_t divider_stalls = 0;
    std::uint64_t total_cycles = 0;

    double cpi() const {
        return retired == 0 ? 0.0
                            : static_cast<double>(total_cycles) /
                                  static_cast<double>(retired);
    }
};

struct TimingRetireResult {
    std::uint64_t retire_cycle = 0;
    bool load_use_hazard = false;
    bool taken_branch_redirect = false;
    bool jump_redirect = false;
    bool divider_startup_stall = false;
};

// Analytical timing model for the current 5-stage RTL pipeline.
//
// Calibrated effects:
//   * 5-stage pipeline fill/drain (N + 4 ideal cycles)
//   * one-cycle load-use interlock
//   * two-cycle penalty for a taken conditional branch
//   * two-cycle penalty for every JAL/JALR redirect
//   * 8-stage pipelined DIV/REM unit, initiation interval 1
//
// The model never reads RTL traces to make a prediction. RTL traces are used
// only after model execution to measure correlation error.
class PipelineTimingModel {
public:
    explicit PipelineTimingModel(const PipelineTimingConfig& config = {});

    void reset();

    // Add a global pipeline hold before the next retirement. Cache misses use
    // this hook because the RTL freezes IF/ID/EX/MEM/WB while imem_ready or
    // dmem_ready is low.
    void add_external_stalls(std::uint32_t cycles);

    // Observe one architecturally retired instruction. branch_taken must come
    // from functional execution of this instruction, not from the RTL trace.
    TimingRetireResult retire(std::uint32_t insn, bool branch_taken);

    const PipelineTimingStats& stats() const { return stats_; }
    const PipelineTimingConfig& config() const { return config_; }

private:
    struct DecodedTimingInfo {
        bool uses_rs1 = false;
        bool uses_rs2 = false;
        bool is_load = false;
        bool is_branch = false;
        bool is_jump = false;
        bool is_div_rem = false;
        std::uint8_t rs1 = 0;
        std::uint8_t rs2 = 0;
        std::uint8_t rd = 0;
    };

    static DecodedTimingInfo decode(std::uint32_t insn);

    PipelineTimingConfig config_;
    PipelineTimingStats stats_{};

    bool previous_was_load_ = false;
    std::uint8_t previous_load_rd_ = 0;
    bool previous_was_div_rem_ = false;
    std::uint64_t accumulated_stalls_ = 0;
};

} // namespace rv32im
