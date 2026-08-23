#include "RV32IMSystemC.hpp"

#include <systemc>

#include <cstdint>
#include <exception>
#include <iostream>
#include <string>

int sc_main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <program.hex> [trace.csv]\n";
        return 2;
    }

    try {
        rv32im::CpuConfig config{};
        config.trace_path = argc >= 3 ? argv[2] : "results/systemc_trace.csv";

        sc_core::sc_clock clk("clk", sc_core::sc_time(1, sc_core::SC_NS));
        sc_core::sc_signal<bool> halted;

        RV32IMSystemC model("rv32im_model", config, argv[1]);
        model.clk(clk);
        model.halted(halted);

        sc_core::sc_start();
        model.cpu().stats().print(std::cout);
        std::cout << "\nSystemC trace: " << config.trace_path << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "ERROR: " << e.what() << '\n';
        return 1;
    }
}
