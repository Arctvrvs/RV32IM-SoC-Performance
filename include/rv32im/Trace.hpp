#pragma once

#include <cstdint>
#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>

namespace rv32im {

struct RetireEvent {
    std::uint64_t cycle = 0;
    std::uint64_t retired = 0;
    std::uint32_t pc = 0;
    std::uint32_t insn = 0;
    std::uint8_t rd = 0;
    std::uint32_t wdata = 0;
    bool reg_write = false;
    std::uint32_t mem_addr = 0;
    bool mem_read = false;
    bool mem_write = false;
};

class TraceWriter {
public:
    TraceWriter() = default;

    explicit TraceWriter(const std::string& path) {
        open(path);
    }

    void open(const std::string& path) {
        out_.open(path);
        if (!out_) {
            throw std::runtime_error("Could not open trace file: " + path);
        }
        out_ << "cycle,retired,pc,insn,rd,wdata,reg_write,mem_addr,mem_read,mem_write\n";
    }

    bool enabled() const { return out_.is_open(); }

    void write(const RetireEvent& e) {
        if (!out_) {
            return;
        }

        const auto flags = out_.flags();
        const auto fill = out_.fill();

        out_ << std::dec << e.cycle << ','
             << e.retired << ','
             << "0x" << std::hex << std::setw(8) << std::setfill('0') << e.pc << ','
             << "0x" << std::hex << std::setw(8) << std::setfill('0') << e.insn << ','
             << std::dec << static_cast<unsigned>(e.rd) << ','
             << "0x" << std::hex << std::setw(8) << std::setfill('0') << e.wdata << ','
             << std::dec << (e.reg_write ? 1 : 0) << ','
             << "0x" << std::hex << std::setw(8) << std::setfill('0') << e.mem_addr << ','
             << std::dec << (e.mem_read ? 1 : 0) << ','
             << (e.mem_write ? 1 : 0) << '\n';

        out_.flags(flags);
        out_.fill(fill);
    }

private:
    std::ofstream out_;
};

} // namespace rv32im
