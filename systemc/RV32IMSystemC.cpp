#include "RV32IMSystemC.hpp"

RV32IMSystemC::RV32IMSystemC(sc_core::sc_module_name name,
                             const rv32im::CpuConfig& config,
                             const std::string& program_path)
    : sc_core::sc_module(name), cpu_(config) {
    cpu_.load_program(program_path);
    cpu_.reset(config.reset_pc);

    SC_METHOD(tick);
    sensitive << clk.pos();
    dont_initialize();
}

void RV32IMSystemC::tick() {
    if (cpu_.halted()) {
        halted.write(true);
        sc_core::sc_stop();
        return;
    }

    cpu_.step();

    if (cpu_.halted()) {
        halted.write(true);
        sc_core::sc_stop();
    }
}
