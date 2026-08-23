#pragma once

#include "rv32im/CpuModel.hpp"
#include <systemc>

#include <string>

class RV32IMSystemC : public sc_core::sc_module {
public:
    sc_core::sc_in<bool> clk{"clk"};
    sc_core::sc_out<bool> halted{"halted"};

    SC_HAS_PROCESS(RV32IMSystemC);

    RV32IMSystemC(sc_core::sc_module_name name,
                  const rv32im::CpuConfig& config,
                  const std::string& program_path);

    const rv32im::CpuModel& cpu() const { return cpu_; }

private:
    void tick();
    rv32im::CpuModel cpu_;
};
