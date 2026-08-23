#include "rv32im/CpuModel.hpp"

#include <climits>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace rv32im {

namespace {

std::uint32_t bits(std::uint32_t value, unsigned hi, unsigned lo) {
    const auto width = hi - lo + 1u;
    const std::uint32_t mask = width == 32u ? 0xffffffffu : ((1u << width) - 1u);
    return (value >> lo) & mask;
}

std::int32_t as_i32(std::uint32_t value) {
    return static_cast<std::int32_t>(value);
}

} // namespace

CpuModel::CpuModel(const CpuConfig& config)
    : config_(config), instruction_memory_(config.memory_size), data_memory_(config.memory_size),
      pc_(config.reset_pc), icache_(config.icache), dcache_(config.dcache) {
    if (!config.trace_path.empty()) {
        trace_.open(config.trace_path);
    }
}

void CpuModel::load_program(const std::string& hex_path, std::uint32_t base_addr) {
    instruction_memory_.load_hex_words(hex_path, base_addr);
}

void CpuModel::load_data(const std::string& hex_path, std::uint32_t base_addr) {
    data_memory_.load_hex_words(hex_path, base_addr);
}

void CpuModel::reset(std::uint32_t pc) {
    regs_.fill(0);
    pc_ = pc;
    halted_ = false;
    cache_overlap_cycles_ = 0;
    dcache_ifstall_replays_ = 0;
    stats_ = {};
    timing_.reset();
    icache_.reset();
    dcache_.reset();
    ifetch_.reset(pc);
}


bool CpuModel::sequential_next_redirect_target(std::uint32_t next_pc, std::uint32_t& target_pc) const {
    if ((next_pc & 0x3u) != 0u) {
        return false;
    }
    const std::uint32_t insn = instruction_memory_.read32(next_pc);
    const unsigned opcode = bits(insn, 6, 0);

    if (opcode == 0x6fu) { // JAL
        const std::int32_t imm_j = sign_extend(
            (bits(insn, 31, 31) << 20u) |
            (bits(insn, 19, 12) << 12u) |
            (bits(insn, 20, 20) << 11u) |
            (bits(insn, 30, 21) << 1u), 21);
        target_pc = next_pc + static_cast<std::uint32_t>(imm_j);
        return true;
    }

    if (opcode == 0x67u && bits(insn, 14, 12) == 0u) { // JALR
        const unsigned rs1 = bits(insn, 19, 15);
        const std::int32_t imm_i = sign_extend(bits(insn, 31, 20), 12);
        target_pc = (regs_[rs1] + static_cast<std::uint32_t>(imm_i)) & ~1u;
        return true;
    }

    if (opcode != 0x63u) {
        return false;
    }

    const unsigned funct3 = bits(insn, 14, 12);
    const unsigned rs1 = bits(insn, 19, 15);
    const unsigned rs2 = bits(insn, 24, 20);
    const std::uint32_t a = regs_[rs1];
    const std::uint32_t b = regs_[rs2];
    bool take = false;
    switch (funct3) {
        case 0x0: take = a == b; break;
        case 0x1: take = a != b; break;
        case 0x4: take = as_i32(a) < as_i32(b); break;
        case 0x5: take = as_i32(a) >= as_i32(b); break;
        case 0x6: take = a < b; break;
        case 0x7: take = a >= b; break;
        default: return false;
    }
    if (!take) {
        return false;
    }
    const std::int32_t imm_b = sign_extend(
        (bits(insn, 31, 31) << 12u) |
        (bits(insn, 7, 7) << 11u) |
        (bits(insn, 30, 25) << 5u) |
        (bits(insn, 11, 8) << 1u), 13);
    target_pc = next_pc + static_cast<std::uint32_t>(imm_b);
    return true;
}

std::uint32_t CpuModel::cache_overlap_credit(std::uint32_t dcache_stall_cycles) const {
    if (!config_.icache.enabled || !config_.dcache.enabled || dcache_stall_cycles <= 1u) {
        return 0;
    }
    const std::uint32_t dcache_tail = dcache_stall_cycles - 1u;
    const std::uint32_t icache_refill = icache_.clean_miss_penalty();
    return dcache_tail < icache_refill ? dcache_tail : icache_refill;
}

std::int32_t CpuModel::sign_extend(std::uint32_t value, unsigned width) {
    const std::uint32_t sign = 1u << (width - 1u);
    const std::uint32_t mask = (width == 32u) ? 0xffffffffu : ((1u << width) - 1u);
    value &= mask;
    return static_cast<std::int32_t>((value ^ sign) - sign);
}

void CpuModel::write_reg(unsigned rd, std::uint32_t value, RetireEvent& event) {
    event.rd = static_cast<std::uint8_t>(rd);
    event.wdata = value;
    event.reg_write = rd != 0;
    if (rd != 0) {
        regs_[rd] = value;
    }
}

[[noreturn]] void CpuModel::illegal(std::uint32_t insn, const char* reason) const {
    std::ostringstream oss;
    oss << "Illegal/unsupported instruction at PC=0x" << std::hex << std::setw(8)
        << std::setfill('0') << pc_ << " insn=0x" << std::setw(8) << insn
        << " (" << reason << ')';
    throw std::runtime_error(oss.str());
}

bool CpuModel::step() {
    if (halted_) {
        return false;
    }
    if (stats_.retired >= config_.max_instructions) {
        throw std::runtime_error("Maximum retired-instruction limit reached");
    }
    if ((pc_ & 0x3u) != 0) {
        throw std::runtime_error("Misaligned instruction fetch");
    }

    const std::uint32_t insn = instruction_memory_.read32(pc_);
    const std::uint32_t old_pc = pc_;

    // Milestone 3B front-end timing.  Fetch requests are modeled independently
    // from retirement PCs.  ensure_through() avoids double-counting PCs that
    // were already fetched ahead of retirement during an older D-cache stall.
    std::uint32_t cache_stalls_this_instruction =
        ifetch_.ensure_through(old_pc, icache_);

    std::uint32_t next_pc = pc_ + 4u;

    const unsigned opcode = bits(insn, 6, 0);
    const unsigned rd = bits(insn, 11, 7);
    const unsigned funct3 = bits(insn, 14, 12);
    const unsigned rs1 = bits(insn, 19, 15);
    const unsigned rs2 = bits(insn, 24, 20);
    const unsigned funct7 = bits(insn, 31, 25);

    const std::uint32_t a = regs_[rs1];
    const std::uint32_t b = regs_[rs2];

    const std::int32_t imm_i = sign_extend(bits(insn, 31, 20), 12);
    const std::int32_t imm_s = sign_extend((bits(insn, 31, 25) << 5u) | bits(insn, 11, 7), 12);
    const std::int32_t imm_b = sign_extend(
        (bits(insn, 31, 31) << 12u) |
        (bits(insn, 7, 7) << 11u) |
        (bits(insn, 30, 25) << 5u) |
        (bits(insn, 11, 8) << 1u), 13);
    const std::int32_t imm_j = sign_extend(
        (bits(insn, 31, 31) << 20u) |
        (bits(insn, 19, 12) << 12u) |
        (bits(insn, 20, 20) << 11u) |
        (bits(insn, 30, 21) << 1u), 21);
    const std::uint32_t imm_u = insn & 0xfffff000u;

    RetireEvent event{};
    event.pc = old_pc;
    event.insn = insn;
    bool branch_taken_this_instruction = false;
    bool jump_this_instruction = false;
    bool terminating_system_this_instruction = false;

    switch (opcode) {
        case 0x37: // LUI
            write_reg(rd, imm_u, event);
            ++stats_.alu;
            break;

        case 0x17: // AUIPC
            write_reg(rd, old_pc + imm_u, event);
            ++stats_.alu;
            break;

        case 0x6f: // JAL
            write_reg(rd, old_pc + 4u, event);
            next_pc = old_pc + static_cast<std::uint32_t>(imm_j);
            jump_this_instruction = true;
            ++stats_.jumps;
            break;

        case 0x67: // JALR
            if (funct3 != 0) illegal(insn, "JALR funct3");
            write_reg(rd, old_pc + 4u, event);
            next_pc = (a + static_cast<std::uint32_t>(imm_i)) & ~1u;
            jump_this_instruction = true;
            ++stats_.jumps;
            break;

        case 0x63: { // BRANCH
            bool take = false;
            switch (funct3) {
                case 0x0: take = (a == b); break;                         // BEQ
                case 0x1: take = (a != b); break;                         // BNE
                case 0x4: take = (as_i32(a) < as_i32(b)); break;          // BLT
                case 0x5: take = (as_i32(a) >= as_i32(b)); break;         // BGE
                case 0x6: take = (a < b); break;                          // BLTU
                case 0x7: take = (a >= b); break;                         // BGEU
                default: illegal(insn, "branch funct3");
            }
            ++stats_.branches;
            if (take) {
                branch_taken_this_instruction = true;
                ++stats_.branches_taken;
                next_pc = old_pc + static_cast<std::uint32_t>(imm_b);
            }
            break;
        }

        case 0x03: { // LOAD
            const std::uint32_t addr = a + static_cast<std::uint32_t>(imm_i);
            std::uint32_t value = 0;
            switch (funct3) {
                case 0x0: value = static_cast<std::uint32_t>(sign_extend(data_memory_.read8(addr), 8)); break;   // LB
                case 0x1: value = static_cast<std::uint32_t>(sign_extend(data_memory_.read16(addr), 16)); break; // LH
                case 0x2: value = data_memory_.read32(addr); break;                                               // LW
                case 0x4: value = data_memory_.read8(addr); break;                                                // LBU
                case 0x5: value = data_memory_.read16(addr); break;                                               // LHU
                default: illegal(insn, "load funct3");
            }
            event.mem_addr = addr;
            event.mem_read = true;
            const auto dcache_access = dcache_.access(addr, false);
            cache_stalls_this_instruction +=
                ifetch_.on_dcache_stall(old_pc, dcache_access.stall_cycles, icache_);
            cache_stalls_this_instruction += dcache_access.stall_cycles;
            write_reg(rd, value, event);
            ++stats_.loads;
            break;
        }

        case 0x23: { // STORE
            const std::uint32_t addr = a + static_cast<std::uint32_t>(imm_s);
            switch (funct3) {
                case 0x0: data_memory_.write8(addr, static_cast<std::uint8_t>(b)); break;   // SB
                case 0x1: data_memory_.write16(addr, static_cast<std::uint16_t>(b)); break; // SH
                case 0x2: data_memory_.write32(addr, b); break;                              // SW
                default: illegal(insn, "store funct3");
            }
            event.mem_addr = addr;
            event.mem_write = true;
            const auto dcache_access = dcache_.access(addr, true);
            const auto ifetch_stalls_during_dcache =
                ifetch_.on_dcache_stall(old_pc, dcache_access.stall_cycles, icache_);

            // Milestone 4B concurrency rule. If this store misses in D$ while
            // the immediately younger control-flow instruction is in EX, and
            // that redirect target is not resident in I$, the two blocking
            // cache waits overlap. The D$ request starts first; the redirected
            // I$ refill can overlap the remaining D$ tail.
            std::uint32_t overlap_credit = 0;
            std::uint32_t redirect_target = 0;
            if (dcache_access.stall_cycles != 0u &&
                ifetch_stalls_during_dcache != 0u &&
                sequential_next_redirect_target(old_pc + 4u, redirect_target) &&
                !icache_.would_hit(redirect_target)) {
                overlap_credit = cache_overlap_credit(dcache_access.stall_cycles);
                cache_overlap_cycles_ += overlap_credit;

                // The D$ response can complete underneath the IF miss. Since
                // dmem_valid is gated by !if_stall in the RTL, the held store
                // is presented once again after IF releases. The just-filled
                // line makes that replay a hit with no additional stall/AXI.
                if (overlap_credit != 0u) {
                    const auto replay = dcache_.access(addr, true);
                    if (!replay.hit || replay.stall_cycles != 0u) {
                        throw std::runtime_error("Expected D-cache filled-line replay hit after IF/D overlap");
                    }
                    ++dcache_ifstall_replays_;
                }
            }

            cache_stalls_this_instruction += ifetch_stalls_during_dcache;
            cache_stalls_this_instruction += dcache_access.stall_cycles;
            cache_stalls_this_instruction -= overlap_credit;
            ++stats_.stores;
            break;
        }

        case 0x13: { // OP-IMM
            std::uint32_t value = 0;
            switch (funct3) {
                case 0x0: value = a + static_cast<std::uint32_t>(imm_i); break;                // ADDI
                case 0x2: value = as_i32(a) < imm_i ? 1u : 0u; break;                           // SLTI
                case 0x3: value = a < static_cast<std::uint32_t>(imm_i) ? 1u : 0u; break;       // SLTIU
                case 0x4: value = a ^ static_cast<std::uint32_t>(imm_i); break;                 // XORI
                case 0x6: value = a | static_cast<std::uint32_t>(imm_i); break;                 // ORI
                case 0x7: value = a & static_cast<std::uint32_t>(imm_i); break;                 // ANDI
                case 0x1:
                    if (funct7 != 0x00) illegal(insn, "SLLI funct7");
                    value = a << (rs2 & 0x1fu);
                    break;
                case 0x5:
                    if (funct7 == 0x00) value = a >> (rs2 & 0x1fu);                              // SRLI
                    else if (funct7 == 0x20) value = static_cast<std::uint32_t>(as_i32(a) >> (rs2 & 0x1fu)); // SRAI
                    else illegal(insn, "SRLI/SRAI funct7");
                    break;
                default: illegal(insn, "OP-IMM funct3");
            }
            write_reg(rd, value, event);
            ++stats_.alu;
            break;
        }

        case 0x33: { // OP / M extension
            std::uint32_t value = 0;
            if (funct7 == 0x01) {
                ++stats_.mul_div;
                const auto sa = static_cast<std::int64_t>(as_i32(a));
                const auto sb = static_cast<std::int64_t>(as_i32(b));
                const auto ua = static_cast<std::uint64_t>(a);
                const auto ub = static_cast<std::uint64_t>(b);
                switch (funct3) {
                    case 0x0: value = static_cast<std::uint32_t>(sa * sb); break;                         // MUL
                    case 0x1: value = static_cast<std::uint32_t>((sa * sb) >> 32); break;                 // MULH
                    case 0x2: value = static_cast<std::uint32_t>((sa * static_cast<std::int64_t>(ub)) >> 32); break; // MULHSU
                    case 0x3: value = static_cast<std::uint32_t>((ua * ub) >> 32); break;                 // MULHU
                    case 0x4: // DIV
                        if (b == 0) value = 0xffffffffu;
                        else if (a == 0x80000000u && b == 0xffffffffu) value = 0x80000000u;
                        else value = static_cast<std::uint32_t>(as_i32(a) / as_i32(b));
                        break;
                    case 0x5: value = b == 0 ? 0xffffffffu : a / b; break;                               // DIVU
                    case 0x6: // REM
                        if (b == 0) value = a;
                        else if (a == 0x80000000u && b == 0xffffffffu) value = 0;
                        else value = static_cast<std::uint32_t>(as_i32(a) % as_i32(b));
                        break;
                    case 0x7: value = b == 0 ? a : a % b; break;                                        // REMU
                    default: illegal(insn, "M-extension funct3");
                }
            } else {
                ++stats_.alu;
                switch (funct3) {
                    case 0x0:
                        if (funct7 == 0x00) value = a + b;                                                // ADD
                        else if (funct7 == 0x20) value = a - b;                                           // SUB
                        else illegal(insn, "ADD/SUB funct7");
                        break;
                    case 0x1:
                        if (funct7 != 0x00) illegal(insn, "SLL funct7");
                        value = a << (b & 0x1fu);
                        break;
                    case 0x2:
                        if (funct7 != 0x00) illegal(insn, "SLT funct7");
                        value = as_i32(a) < as_i32(b) ? 1u : 0u;
                        break;
                    case 0x3:
                        if (funct7 != 0x00) illegal(insn, "SLTU funct7");
                        value = a < b ? 1u : 0u;
                        break;
                    case 0x4:
                        if (funct7 != 0x00) illegal(insn, "XOR funct7");
                        value = a ^ b;
                        break;
                    case 0x5:
                        if (funct7 == 0x00) value = a >> (b & 0x1fu);                                     // SRL
                        else if (funct7 == 0x20) value = static_cast<std::uint32_t>(as_i32(a) >> (b & 0x1fu)); // SRA
                        else illegal(insn, "SRL/SRA funct7");
                        break;
                    case 0x6:
                        if (funct7 != 0x00) illegal(insn, "OR funct7");
                        value = a | b;
                        break;
                    case 0x7:
                        if (funct7 != 0x00) illegal(insn, "AND funct7");
                        value = a & b;
                        break;
                    default: illegal(insn, "OP funct3");
                }
            }
            write_reg(rd, value, event);
            break;
        }

        case 0x0f: // FENCE/FENCE.I: no-op in functional model
            ++stats_.alu;
            break;

        case 0x73: // SYSTEM
            // For this starter, ECALL/EBREAK are clean termination points.
            // CSR instructions will be added if your exact RTL workloads need them.
            if (insn == 0x00000073u || insn == 0x00100073u) {
                terminating_system_this_instruction = true;
                halted_ = true;
            } else {
                illegal(insn, "CSR/system instruction not implemented in Milestone 1");
            }
            break;

        default:
            illegal(insn, "unknown opcode");
    }

    regs_[0] = 0;
    pc_ = next_pc;

    // Milestone 3C redirect-aware front end. A taken conditional branch
    // resolves in EX only after two younger sequential fetch requests have
    // escaped. Their misses are real pipeline stalls; then IF restarts at the
    // architectural target, including for backward loops/conflict refetches.
    if (branch_taken_this_instruction) {
        cache_stalls_this_instruction +=
            ifetch_.on_taken_branch(old_pc, next_pc, icache_);
    }

    // Milestone 3D: JAL/JALR use the same two-younger-request EX redirect
    // mechanism. Resetting the IF stream at the target is essential for
    // backward jumps and call/return cache conflicts.
    if (jump_this_instruction) {
        cache_stalls_this_instruction +=
            ifetch_.on_jump_redirect(old_pc, next_pc, icache_);
    }

    // ECALL/EBREAK do not stop IF immediately in the RTL.  Two younger PCs are
    // fetched while the SYSTEM instruction drains toward WB, and the final PC
    // is observed for two additional hit cycles while halt commits.
    if (terminating_system_this_instruction) {
        cache_stalls_this_instruction += ifetch_.on_system_drain(old_pc, icache_);
    }

    // Cache misses globally hold the RTL pipeline. Add those hold cycles before
    // retiring the instruction whose execution exposed the miss.
    timing_.add_external_stalls(cache_stalls_this_instruction);

    // Feed the architecturally executed instruction into the analytical
    // 5-stage pipeline timing model.  This prediction is derived only from
    // instruction semantics/dependencies; it never reads the RTL trace.
    const auto timing_result = timing_.retire(insn, branch_taken_this_instruction);
    const auto& timing_stats = timing_.stats();

    stats_.retired = timing_stats.retired;
    stats_.cycles = timing_stats.total_cycles;
    stats_.base_instruction_cycles = timing_stats.base_instruction_cycles;
    stats_.pipeline_fill_drain = timing_stats.pipeline_fill_drain;
    stats_.stall_load_use = timing_stats.load_use_stalls;
    stats_.stall_branch_redirect = timing_stats.branch_redirect_stalls;
    stats_.stall_jump_redirect = timing_stats.jump_redirect_stalls;
    stats_.stall_divider = timing_stats.divider_stalls;

    const auto& i_stats = icache_.stats();
    const auto& d_stats = dcache_.stats();
    stats_.stall_icache = i_stats.stall_cycles;
    stats_.stall_dcache = d_stats.stall_cycles;
    stats_.stall_cache_overlap = cache_overlap_cycles_;

    // Effective load-use and divider holds keep IF valid. Those repeated
    // requests are already-resident hits and therefore change access/hit
    // counters without changing miss latency. Simultaneous cache-overlap cycles
    // are already represented by the cache-hold request stream, so they are
    // not counted a second time here.
    std::uint64_t pipeline_hold_replays = 0;
    if (config_.icache.enabled) {
        pipeline_hold_replays = timing_stats.load_use_stalls + timing_stats.divider_stalls;
        const auto duplicate = cache_overlap_cycles_ < pipeline_hold_replays
            ? cache_overlap_cycles_ : pipeline_hold_replays;
        pipeline_hold_replays -= duplicate;
    }
    stats_.icache_pipeline_hold_replays = pipeline_hold_replays;
    stats_.icache_accesses = i_stats.accesses + pipeline_hold_replays;
    stats_.icache_hits = i_stats.hits + pipeline_hold_replays;
    stats_.icache_misses = i_stats.misses;
    stats_.dcache_ifstall_replays = dcache_ifstall_replays_;
    stats_.dcache_accesses = d_stats.accesses;
    stats_.dcache_hits = d_stats.hits;
    stats_.dcache_misses = d_stats.misses;
    stats_.dcache_writebacks = d_stats.writebacks;
    stats_.axi_read_transactions = i_stats.read_transactions + d_stats.read_transactions;
    stats_.axi_write_transactions = d_stats.write_transactions;

    event.cycle = timing_result.retire_cycle;
    event.retired = stats_.retired;
    trace_.write(event);

    return !halted_;
}

void CpuModel::run() {
    while (!halted_) {
        step();
    }
}

} // namespace rv32im
