#include "rv32im/CpuModel.hpp"

#include <cmath>
#include <cstdint>
#include <exception>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void usage(const char* argv0) {
    std::cout
        << "RV32IM functional + analytical pipeline performance model\n\n"
        << "Usage:\n  " << argv0 << " <program.hex> [options]\n\n"
        << "Options:\n"
        << "  --trace <path>          Model retirement CSV (default: results/model_trace.csv)\n"
        << "  --dmem-hex <path>       Optional data-memory hex image\n"
        << "  --rtl-trace <path>      Optional RTL CSV for cycle/CPI summary correlation\n"
        << "  --start-pc <value>      Reset PC, decimal or 0x-prefixed hex (default: 0)\n"
        << "  --mem-size <bytes>      Memory size (default: 1048576)\n"
        << "  --max-insns <count>     Safety limit (default: 10000000)\n"
        << "  --dump-regs             Print all integer registers at the end\n"
        << "  --enable-icache         Enable analytical direct-mapped I-cache\n"
        << "  --enable-dcache         Enable analytical write-back D-cache\n"
        << "  --enable-caches         Enable both I-cache and D-cache\n"
        << "  --icache-lines <N>      I-cache lines (power of two; default 64)\n"
        << "  --dcache-lines <N>      D-cache lines (power of two; default 64)\n"
        << "  --memory-latency <N>    AXI backing-memory LATENCY (default 3)\n";
}

std::uint64_t parse_u64(const std::string& text) {
    std::size_t used = 0;
    const auto value = std::stoull(text, &used, 0);
    if (used != text.size()) {
        throw std::invalid_argument("Invalid integer: " + text);
    }
    return value;
}

std::vector<std::string> split_csv(const std::string& line) {
    std::vector<std::string> fields;
    std::stringstream ss(line);
    std::string field;
    while (std::getline(ss, field, ',')) {
        fields.push_back(field);
    }
    return fields;
}

struct RtlTraceSummary {
    std::uint64_t rows = 0;
    std::uint64_t first_retire_cycle = 0;
    std::uint64_t last_retire_cycle = 0;
};

RtlTraceSummary read_rtl_summary(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        throw std::runtime_error("Could not open RTL trace: " + path);
    }

    std::string line;
    if (!std::getline(in, line)) {
        throw std::runtime_error("RTL trace is empty: " + path);
    }

    RtlTraceSummary summary{};
    while (std::getline(in, line)) {
        if (line.empty()) {
            continue;
        }
        const auto fields = split_csv(line);
        if (fields.size() < 2) {
            continue;
        }
        const auto cycle = parse_u64(fields[0]);
        if (summary.rows == 0) {
            summary.first_retire_cycle = cycle;
        }
        summary.last_retire_cycle = cycle;
        ++summary.rows;
    }

    if (summary.rows == 0) {
        throw std::runtime_error("RTL trace has no retirement rows: " + path);
    }
    return summary;
}

void print_rtl_correlation(const rv32im::PerformanceStats& model,
                           const std::string& rtl_trace_path) {
    const auto rtl = read_rtl_summary(rtl_trace_path);
    const double rtl_cpi = rtl.rows == 0
        ? 0.0
        : static_cast<double>(rtl.last_retire_cycle) / static_cast<double>(rtl.rows);
    const double cycle_error = rtl.last_retire_cycle == 0
        ? 0.0
        : 100.0 * std::fabs(static_cast<double>(model.cycles) -
                            static_cast<double>(rtl.last_retire_cycle)) /
              static_cast<double>(rtl.last_retire_cycle);

    std::cout << "\n=== RTL performance correlation ===\n"
              << "model retired           : " << model.retired << '\n'
              << "RTL retired             : " << rtl.rows << '\n'
              << "first RTL retire cycle  : " << rtl.first_retire_cycle << '\n'
              << "model cycles            : " << model.cycles << '\n'
              << "RTL cycles              : " << rtl.last_retire_cycle << '\n'
              << "model CPI               : " << std::fixed << std::setprecision(4)
              << model.cpi() << '\n'
              << "RTL CPI                 : " << rtl_cpi << '\n'
              << "cycle error             : " << std::setprecision(2) << cycle_error << "%\n";

    if (model.retired == rtl.rows && model.cycles == rtl.last_retire_cycle) {
        std::cout << "result                  : PASS (exact aggregate timing correlation)\n";
    } else {
        std::cout << "result                  : CHECK detailed retirement-cycle comparison\n";
    }
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        usage(argv[0]);
        return 2;
    }

    std::string program = argv[1];
    std::string trace_path = "results/model_trace.csv";
    std::string rtl_trace_path;
    std::string dmem_hex_path;
    rv32im::CpuConfig config{};
    config.icache.lines = 64;
    config.icache.line_bytes = 4;
    config.icache.memory_latency = 3;
    config.icache.write_back = false;
    config.dcache.lines = 64;
    config.dcache.line_bytes = 4;
    config.dcache.memory_latency = 3;
    config.dcache.write_back = true;
    bool dump_regs = false;

    try {
        for (int i = 2; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--trace" && i + 1 < argc) {
                trace_path = argv[++i];
            } else if (arg == "--dmem-hex" && i + 1 < argc) {
                dmem_hex_path = argv[++i];
            } else if (arg == "--rtl-trace" && i + 1 < argc) {
                rtl_trace_path = argv[++i];
            } else if (arg == "--start-pc" && i + 1 < argc) {
                config.reset_pc = static_cast<std::uint32_t>(parse_u64(argv[++i]));
            } else if (arg == "--mem-size" && i + 1 < argc) {
                config.memory_size = static_cast<std::size_t>(parse_u64(argv[++i]));
            } else if (arg == "--max-insns" && i + 1 < argc) {
                config.max_instructions = parse_u64(argv[++i]);
            } else if (arg == "--dump-regs") {
                dump_regs = true;
            } else if (arg == "--enable-icache") {
                config.icache.enabled = true;
            } else if (arg == "--enable-dcache") {
                config.dcache.enabled = true;
            } else if (arg == "--enable-caches") {
                config.icache.enabled = true;
                config.dcache.enabled = true;
            } else if (arg == "--icache-lines" && i + 1 < argc) {
                config.icache.lines = static_cast<std::size_t>(parse_u64(argv[++i]));
            } else if (arg == "--dcache-lines" && i + 1 < argc) {
                config.dcache.lines = static_cast<std::size_t>(parse_u64(argv[++i]));
            } else if (arg == "--memory-latency" && i + 1 < argc) {
                const auto latency = static_cast<std::uint32_t>(parse_u64(argv[++i]));
                config.icache.memory_latency = latency;
                config.dcache.memory_latency = latency;
            } else if (arg == "--help" || arg == "-h") {
                usage(argv[0]);
                return 0;
            } else {
                throw std::invalid_argument("Unknown/incomplete option: " + arg);
            }
        }

        config.trace_path = trace_path;
        rv32im::CpuModel cpu(config);
        cpu.load_program(program);
        if (!dmem_hex_path.empty()) {
            cpu.load_data(dmem_hex_path);
        }
        cpu.reset(config.reset_pc);
        cpu.run();
        cpu.stats().print(std::cout);

        if (!rtl_trace_path.empty()) {
            print_rtl_correlation(cpu.stats(), rtl_trace_path);
        }

        if (dump_regs) {
            std::cout << "\n=== Registers ===\n";
            for (unsigned i = 0; i < 32; ++i) {
                std::cout << 'x' << std::setw(2) << std::setfill('0') << i
                          << " = 0x" << std::hex << std::setw(8) << cpu.reg(i)
                          << std::dec << std::setfill(' ') << '\n';
            }
        }

        std::cout << "\nModel trace: " << trace_path << '\n';
        if (!rtl_trace_path.empty()) {
            std::cout << "RTL trace  : " << rtl_trace_path << '\n';
        }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "ERROR: " << e.what() << '\n';
        return 1;
    }
}
