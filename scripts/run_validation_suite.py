#!/usr/bin/env python3
"""Build the model, run all directed validation workloads, and correlate VCS traces.

This script is intended for Windows but is also portable to Linux/macOS.
The model predictions for all calibrated tests, including the 8-stage divider,
are frozen below so later model changes cannot silently rewrite the validation target.
"""
from __future__ import print_function

import argparse
import csv
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
BUILD = os.path.join(ROOT, "build")
RESULTS = os.path.join(ROOT, "results", "validation")

TESTS = [
    ("smoke", os.path.join(ROOT, "workloads", "smoke.hex"), "validate", 17),
    ("no_hazards", os.path.join(ROOT, "workloads", "validation", "no_hazards.hex"), "validate", 14),
    ("load_hazards", os.path.join(ROOT, "workloads", "validation", "load_hazards.hex"), "validate", 18),
    ("branches", os.path.join(ROOT, "workloads", "validation", "branches.hex"), "validate", 21),
    ("divider", os.path.join(ROOT, "workloads", "validation", "divider.hex"), "validate", 20),
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-only", action="store_true",
                    help="Generate/freeze model predictions without requiring VCS traces")
    ap.add_argument("--require-rtl", action="store_true",
                    help="Fail if any VCS validation trace is missing")
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

    for name, workload, mode, frozen_cycles in TESTS:
        model_trace = os.path.join(RESULTS, "model_" + name + ".csv")
        model_log = os.path.join(RESULTS, "model_" + name + ".log")
        rtl_trace = os.path.join(RESULTS, "rtl_" + name + ".csv")

        cmd = [exe, workload, "--trace", model_trace]
        rc = run(cmd, model_log)
        if rc != 0:
            print("FAIL: model execution failed for {}. See {}".format(name, model_log))
            failure = True
            summary.append((name, mode, "FAIL", "N/A", 0, 0, 0.0))
            continue

        model = load_trace(model_trace)
        model_cycles = model[-1]["cycle"] if model else 0
        if model_cycles != frozen_cycles:
            print("FAIL: {} model prediction changed: frozen={} current={}".format(
                name, frozen_cycles, model_cycles))
            failure = True

        if args.model_only or not os.path.isfile(rtl_trace):
            if not args.model_only and args.require_rtl:
                print("FAIL: missing {}".format(rtl_trace))
                failure = True
            summary.append((name, mode, "WAIT", "WAIT", model_cycles, 0, 0.0))
            continue

        rtl = load_trace(rtl_trace)
        arch_ok, detail = compare_arch(model, rtl)
        rtl_cycles = rtl[-1]["cycle"] if rtl else 0
        err = 0.0 if rtl_cycles == 0 else 100.0 * abs(model_cycles - rtl_cycles) / float(rtl_cycles)
        timing_ok = model_cycles == rtl_cycles and len(model) == len(rtl)

        if not arch_ok:
            failure = True
        if mode == "validate" and not timing_ok:
            failure = True

        summary.append((
            name,
            mode,
            "PASS" if arch_ok else "FAIL",
            ("PASS" if timing_ok else "FAIL") if mode == "validate" else "MEASURE",
            model_cycles,
            rtl_cycles,
            err,
        ))
        print("{}: arch={} timing={} model={} rtl={} error={:.2f}% ({})".format(
            name, arch_ok, timing_ok if mode == "validate" else "MEASURE",
            model_cycles, rtl_cycles, err, detail))

    print("\n============================================================")
    print("WINDOWS VALIDATION SUMMARY")
    print("============================================================")
    print("{:<16} {:<9} {:<7} {:<9} {:>7} {:>7} {:>9}".format(
        "test", "mode", "arch", "timing", "model", "rtl", "error"))
    print("-" * 72)
    for row in summary:
        name, mode, arch, timing, mc, rc, err = row
        print("{:<16} {:<9} {:<7} {:<9} {:>7} {:>7} {:>8.2f}%".format(
            name, mode, arch, timing, mc, rc, err))

    summary_path = os.path.join(RESULTS, "windows_validation_summary.csv")
    with open(summary_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["test", "mode", "architectural", "timing", "model_cycles", "rtl_cycles", "cycle_error_pct"])
        for row in summary:
            w.writerow(row)
    print("\nSummary CSV: {}".format(summary_path))

    if args.model_only:
        print("\nModel predictions are frozen. Run the VCS validation bundle next.")
    elif any(row[2] == "WAIT" for row in summary):
        print("\nSome RTL traces are missing. Extract RV32IM_VCS_Validation_Results.zip at this project root, then rerun.")

    return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
