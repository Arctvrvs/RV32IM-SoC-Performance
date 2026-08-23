#!/usr/bin/env python3
"""Architectural and optional retirement-cycle correlation for model vs RTL."""

import argparse
import csv
import sys


def num(text):
    text = (text or "0").strip()
    if not text:
        return 0
    try:
        return int(text, 0)
    except ValueError:
        return int(text, 16)


def load(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"pc", "insn", "rd", "wdata", "reg_write"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("{}: missing CSV columns: {}".format(path, sorted(missing)))

        for i, r in enumerate(reader, start=2):
            rows.append({
                "row": i,
                "cycle": num(r.get("cycle", "0")),
                "retired": num(r.get("retired", str(len(rows) + 1))),
                "pc": num(r["pc"]),
                "insn": num(r["insn"]),
                "rd": num(r["rd"]),
                "wdata": num(r["wdata"]),
                "reg_write": num(r["reg_write"]),
            })
    return rows


def fmt(x):
    return "0x{:08x}".format(x & 0xFFFFFFFF)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("model")
    p.add_argument("rtl")
    p.add_argument("--max-mismatches", type=int, default=20)
    p.add_argument("--compare-cycle", action="store_true",
                   help="Also require model/RTL retirement-cycle values to match.")
    args = p.parse_args()

    model = load(args.model)
    rtl = load(args.rtl)
    n = min(len(model), len(rtl))
    mismatches = 0

    print("RV32IM architectural correlation")
    print("================================")
    print("model retired : {}".format(len(model)))
    print("rtl retired   : {}".format(len(rtl)))

    for i in range(n):
        m = model[i]
        r = rtl[i]
        fields = []

        if m["pc"] != r["pc"]:
            fields.append("pc model={} rtl={}".format(fmt(m["pc"]), fmt(r["pc"])))
        if m["insn"] != r["insn"]:
            fields.append("insn model={} rtl={}".format(fmt(m["insn"]), fmt(r["insn"])))
        if m["reg_write"] != r["reg_write"]:
            fields.append("reg_write model={} rtl={}".format(m["reg_write"], r["reg_write"]))

        if m["reg_write"] or r["reg_write"]:
            if m["rd"] != r["rd"]:
                fields.append("rd model=x{} rtl=x{}".format(m["rd"], r["rd"]))
            if m["wdata"] != r["wdata"]:
                fields.append("wdata model={} rtl={}".format(fmt(m["wdata"]), fmt(r["wdata"])))

        if args.compare_cycle and m["cycle"] != r["cycle"]:
            fields.append("cycle model={} rtl={}".format(m["cycle"], r["cycle"]))

        if fields:
            mismatches += 1
            print("\nMismatch at retirement #{}:".format(i + 1))
            for field in fields:
                print("  " + field)
            if mismatches >= args.max_mismatches:
                print("\nStopping after {} mismatches.".format(mismatches))
                break

    if len(model) != len(rtl):
        mismatches += 1
        print("\nLength mismatch: model={}, rtl={}".format(len(model), len(rtl)))

    if mismatches == 0:
        print("\nPASS: {} retired instructions match architecturally.".format(n))
        if args.compare_cycle:
            print("PASS: retirement-cycle timing also matches RTL exactly.")
        else:
            print("Use --compare-cycle to include Milestone 2 timing correlation.")
        return 0

    print("\nFAIL: {} mismatch(es) detected.".format(mismatches))
    return 1


if __name__ == "__main__":
    sys.exit(main())
