#include "rv32im/PipelineTimingModel.hpp"

namespace rv32im {

namespace {

std::uint32_t bits(std::uint32_t value, unsigned hi, unsigned lo) {
    const auto width = hi - lo + 1u;
    const std::uint32_t mask = width == 32u ? 0xffffffffu : ((1u << width) - 1u);
    return (value >> lo) & mask;
}

} // namespace

PipelineTimingModel::PipelineTimingModel(const PipelineTimingConfig& config)
    : config_(config) {
    reset();
}

void PipelineTimingModel::reset() {
    stats_ = {};
    previous_was_load_ = false;
    previous_load_rd_ = 0;
    previous_was_div_rem_ = false;
    accumulated_stalls_ = 0;
}

void PipelineTimingModel::add_external_stalls(std::uint32_t cycles) {
    accumulated_stalls_ += cycles;
}

PipelineTimingModel::DecodedTimingInfo PipelineTimingModel::decode(std::uint32_t insn) {
    DecodedTimingInfo info{};

    const auto opcode = bits(insn, 6, 0);
    const auto funct3 = bits(insn, 14, 12);
    const auto funct7 = bits(insn, 31, 25);

    info.rd = static_cast<std::uint8_t>(bits(insn, 11, 7));
    info.rs1 = static_cast<std::uint8_t>(bits(insn, 19, 15));
    info.rs2 = static_cast<std::uint8_t>(bits(insn, 24, 20));

    switch (opcode) {
        case 0x67: // JALR
            info.uses_rs1 = true;
            info.is_jump = true;
            break;

        case 0x6f: // JAL
            info.is_jump = true;
            break;

        case 0x63: // conditional branches
            info.uses_rs1 = true;
            info.uses_rs2 = true;
            info.is_branch = true;
            break;

        case 0x03: // loads
            info.uses_rs1 = true;
            info.is_load = true;
            break;

        case 0x23: // stores
            // Address rs1 is needed in EX, but store-data rs2 is not needed
            // until MEM. The RTL forwards load data into the MEM-stage store
            // path, so `lw xN,...; sw xN,...` does not take a load-use bubble.
            info.uses_rs1 = true;
            info.uses_rs2 = false;
            break;

        case 0x13: // OP-IMM
            info.uses_rs1 = true;
            break;

        case 0x33: // OP / RV32M
            info.uses_rs1 = true;
            info.uses_rs2 = true;
            // funct7=1, funct3=4..7 are DIV/DIVU/REM/REMU. MUL variants
            // remain single-cycle in the current RTL retirement timing.
            info.is_div_rem = (funct7 == 0x01u && funct3 >= 0x04u);
            break;

        default:
            // LUI/AUIPC/JAL/FENCE/SYSTEM do not consume an integer source
            // register in a way that creates the load-use interlock modeled here.
            break;
    }

    return info;
}

TimingRetireResult PipelineTimingModel::retire(std::uint32_t insn, bool branch_taken) {
    const auto current = decode(insn);
    TimingRetireResult result{};

    // A load result is not available soon enough for the immediately following
    // instruction. The RTL inserts one bubble when that instruction consumes rd.
    if (previous_was_load_ && previous_load_rd_ != 0 &&
        ((current.uses_rs1 && current.rs1 == previous_load_rd_) ||
         (current.uses_rs2 && current.rs2 == previous_load_rd_))) {
        result.load_use_hazard = true;
        stats_.load_use_stalls += config_.load_use_penalty;
        accumulated_stalls_ += config_.load_use_penalty;
    }

    // Divider timing is a pre-retirement stall. Characterization showed that the
    // first DIV/REM in each contiguous burst retires 7 cycles later than the
    // baseline model (8-stage latency), while immediately consecutive divider
    // operations retire one per cycle (II=1). Any non-divider between them ends
    // the burst and the next divider pays startup again.
    if (current.is_div_rem) {
        std::uint32_t divider_penalty = 0;
        if (!previous_was_div_rem_) {
            divider_penalty = config_.divider_latency > 0
                ? config_.divider_latency - 1u
                : 0u;
            result.divider_startup_stall = divider_penalty != 0;
        } else if (config_.divider_initiation_interval > 1u) {
            divider_penalty = config_.divider_initiation_interval - 1u;
        }

        stats_.divider_stalls += divider_penalty;
        accumulated_stalls_ += divider_penalty;
    }

    ++stats_.retired;
    stats_.base_instruction_cycles = stats_.retired;
    stats_.pipeline_fill_drain =
        stats_.retired == 0 ? 0 : (config_.pipeline_depth > 0 ? config_.pipeline_depth - 1u : 0u);

    // The current instruction retires after stalls caused by older instructions,
    // load-use interlocks immediately in front of it, and divider startup when
    // this instruction starts a new divider burst.
    result.retire_cycle = stats_.retired + stats_.pipeline_fill_drain + accumulated_stalls_;

    // A taken branch does not delay its own retirement; it squashes younger
    // wrong-path instructions, so its penalty applies to following retirement(s).
    if (current.is_branch && branch_taken) {
        result.taken_branch_redirect = true;
        stats_.branch_redirect_stalls += config_.taken_branch_penalty;
        accumulated_stalls_ += config_.taken_branch_penalty;
    }

    // JAL and JALR always redirect control flow. Directed VCS tests show the
    // same two-cycle EX redirect penalty as a taken conditional branch. Like
    // the branch penalty, it delays younger retirements rather than the jump's
    // own retirement.
    if (current.is_jump) {
        result.jump_redirect = true;
        stats_.jump_redirect_stalls += config_.jump_redirect_penalty;
        accumulated_stalls_ += config_.jump_redirect_penalty;
    }

    stats_.total_cycles = stats_.retired + stats_.pipeline_fill_drain + accumulated_stalls_;

    previous_was_load_ = current.is_load;
    previous_load_rd_ = current.is_load ? current.rd : 0;
    previous_was_div_rem_ = current.is_div_rem;

    return result;
}

} // namespace rv32im
