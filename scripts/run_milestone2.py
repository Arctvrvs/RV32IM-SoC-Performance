#!/usr/bin/env python3
"""Build and run the Milestone 2 analytical pipeline timing correlation.

Written to remain compatible with Python 3.6+.
"""

import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
BUILD = os.path.join(ROOT, "build")
RESULTS = os.path.join(ROOT, "results")
MODEL_TRACE = os.path.join(RESULTS, "model_trace.csv")
RTL_TRACE = os.path.join(RESULTS, "rtl_trace.csv")
WORKLOAD = os.path.join(ROOT, "workloads", "smoke.hex")


def run(cmd):
    print("\n+ " + " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def find_exe():
    candidates = [
        os.path.join(BUILD, "Release", "rv32im_model.exe"),
        os.path.join(BUILD, "Debug", "rv32im_model.exe"),
        os.path.join(BUILD, "rv32im_model.exe"),
        os.path.join(BUILD, "rv32im_model"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise RuntimeError("rv32im_model executable not found after build")


def main():
    if not os.path.isfile(RTL_TRACE):
        print("ERROR: results/rtl_trace.csv is missing.")
        print("Copy the VCS result back from the Linux VM first.")
        return 2

    if not os.path.isdir(RESULTS):
        os.makedirs(RESULTS)

    run(["cmake", "-S", ".", "-B", "build", "-DRV32IM_BUILD_SYSTEMC=OFF"])
    run(["cmake", "--build", "build", "--config", "Release"])

    exe = find_exe()
    run([
        exe,
        WORKLOAD,
        "--trace", MODEL_TRACE,
        "--rtl-trace", RTL_TRACE,
        "--dump-regs",
    ])

    run([
        sys.executable,
        os.path.join(ROOT, "scripts", "compare_traces.py"),
        MODEL_TRACE,
        RTL_TRACE,
        "--compare-cycle",
    ])

    print("\n============================================================")
    print("Milestone 2 smoke timing correlation completed.")
    print("Expected smoke result: 17 model cycles, 17 RTL cycles, 0.00% error.")
    print("============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
