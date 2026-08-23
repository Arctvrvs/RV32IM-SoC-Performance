#!/usr/bin/env python3
"""Validate the calibrated 8-stage pipelined divider timing model against VCS traces.

Characterization established this RTL rule:
  * first DIV/DIVU/REM/REMU in a contiguous burst pays +7 cycles
  * immediately consecutive divider operations retire one per cycle (II=1)
  * a non-divider instruction ends the burst; the next divider pays +7 again

The expected model cycles and retirement-cycle sequences below are now frozen.
"""
from __future__ import print_function

import argparse
import csv
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
BUILD = os.path.join(ROOT, "build")
RESULTS = os.path.join(ROOT, "results", "divider_characterization")
WORKLOADS = os.path.join(ROOT, "workloads", "divider_characterization")

TESTS = [
    ("divider_single", 15, [5, 6, 14, 15], "single DIV latency"),
    ("divider_dependent", 16, [5, 6, 14, 15, 16], "consumer immediately depends on DIV result"),
    ("divider_independent", 17, [5, 6, 14, 15, 16, 17], "independent instructions follow DIV"),
    ("divider_back_to_back", 18, [5, 6, 14, 15, 16, 17, 18], "DIV/DIVU/REM/REMU one per cycle"),
    ("divider_idle_gap", 31, [5, 6, 14, 15, 16, 17, 18, 19, 20, 21, 22, 30, 31],
     "second DIV after eight independent instructions"),
]


def run(cmd, capture_path=None):
    print("\n+ " + " ".join(cmd))
    if capture_path is None:
        return subprocess.call(cmd, cwd=ROOT)
    with open(capture_path, "w") as out:
        return subprocess.call(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)


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


def num(text):
    return int((text or "0").strip(), 0)


def load_trace(path):
    rows = []
    with open(path, "r", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "cycle": num(r.get("cycle", "0")),
                "pc": num(r["pc"]),
                "insn": num(r["insn"]),
                "rd": num(r["rd"]),
                "wdata": num(r["wdata"]),
                "reg_write": num(r["reg_write"]),
            })
    return rows


def compare_arch(model, rtl):
    if len(model) != len(rtl):
        return False, "retired count model={} rtl={}".format(len(model), len(rtl))
    for i, (m, r) in enumerate(zip(model, rtl), 1):
        if m["pc"] != r["pc"]:
            return False, "#{} PC mismatch".format(i)
        if m["insn"] != r["insn"]:
            return False, "#{} instruction mismatch".format(i)
        if m["reg_write"] != r["reg_write"]:
            return False, "#{} reg_write mismatch".format(i)
        if m["reg_write"] and (m["rd"] != r["rd"] or m["wdata"] != r["wdata"]):
            return False, "#{} register result mismatch".format(i)
    return True, "{} retirements match".format(len(model))


def cycle_values(rows):
    return [r["cycle"] for r in rows]


def cycle_list(rows):
    return ",".join(str(v) for v in cycle_values(rows))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-only", action="store_true",
                    help="Generate calibrated model traces without requiring VCS traces")
    ap.add_argument("--require-rtl", action="store_true",
                    help="Fail if a VCS characterization trace is missing")
    args = ap.parse_args()

    if not os.path.isdir(RESULTS):
        os.makedirs(RESULTS)

    rc = run(["cmake", "-S", ".", "-B", "build", "-DRV32IM_BUILD_SYSTEMC=OFF"])
    if rc != 0:
        return rc
    rc = run(["cmake", "--build", "build", "--config", "Release"])
    if rc != 0:
        return rc

    exe = find_exe()
    summary = []
    failure = False

    for name, expected_cycles, expected_retire_cycles, purpose in TESTS:
        workload = os.path.join(WORKLOADS, name + ".hex")
        model_trace = os.path.join(RESULTS, "model_" + name + ".csv")
        model_log = os.path.join(RESULTS, "model_" + name + ".log")
        rtl_trace = os.path.join(RESULTS, "rtl_" + name + ".csv")

        rc = run([exe, workload, "--trace", model_trace], model_log)
        if rc != 0:
            print("FAIL: model execution failed for {}".format(name))
            failure = True
            continue

        model = load_trace(model_trace)
        model_cycles = model[-1]["cycle"] if model else 0
        model_retire_cycles = cycle_values(model)
        model_frozen_ok = (model_cycles == expected_cycles and
                           model_retire_cycles == expected_retire_cycles)
        if not model_frozen_ok:
            print("FAIL: {} calibrated prediction changed".format(name))
            print("  expected cycles : {}".format(expected_retire_cycles))
            print("  current cycles  : {}".format(model_retire_cycles))
            failure = True

        if args.model_only or not os.path.isfile(rtl_trace):
            if args.require_rtl and not args.model_only:
                print("FAIL: missing {}".format(rtl_trace))
                failure = True
            summary.append((name, "WAIT", "WAIT", model_cycles, 0, 0.0, purpose,
                            cycle_list(model), ""))
            continue

        rtl = load_trace(rtl_trace)
        arch_ok, detail = compare_arch(model, rtl)
        rtl_cycles = rtl[-1]["cycle"] if rtl else 0
        error = 0.0 if rtl_cycles == 0 else 100.0 * abs(model_cycles - rtl_cycles) / float(rtl_cycles)
        exact_timing = model_retire_cycles == cycle_values(rtl)

        if not arch_ok or not exact_timing:
            failure = True

        print("{}: arch={} timing={} model={} rtl={} error={:.2f}% ({})".format(
            name, arch_ok, exact_timing, model_cycles, rtl_cycles, error, detail))
        print("  model retire cycles: {}".format(cycle_list(model)))
        print("  RTL   retire cycles: {}".format(cycle_list(rtl)))

        summary.append((name,
                        "PASS" if arch_ok else "FAIL",
                        "PASS" if exact_timing else "FAIL",
                        model_cycles, rtl_cycles, error, purpose,
                        cycle_list(model), cycle_list(rtl)))

    print("\n" + "=" * 104)
    print("DIVIDER CALIBRATION VALIDATION SUMMARY")
    print("=" * 104)
    print("{:<24} {:<7} {:<8} {:>7} {:>7} {:>9}  {}".format(
        "test", "arch", "timing", "model", "rtl", "error", "purpose"))
    print("-" * 104)
    for row in summary:
        name, arch, timing, mc, rc_, err, purpose, _, _ = row
        print("{:<24} {:<7} {:<8} {:>7} {:>7} {:>8.2f}%  {}".format(
            name, arch, timing, mc, rc_, err, purpose))

    summary_path = os.path.join(RESULTS, "divider_calibration_validation_summary.csv")
    with open(summary_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["test", "architectural", "timing", "model_cycles", "rtl_cycles",
                    "cycle_error_pct", "purpose", "model_retire_cycles", "rtl_retire_cycles"])
        for row in summary:
            w.writerow(row)
    print("\nSummary CSV: {}".format(summary_path))

    if args.model_only:
        print("\nCalibrated divider predictions generated. Add the existing VCS traces and rerun --require-rtl.")
    elif not failure:
        print("\nPASS: calibrated divider timing matches every characterization trace exactly.")

    return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
