#!/usr/bin/env python3
"""Small first-pass workload/performance report from a retirement CSV."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

OPCODES = {
    0x03: "load",
    0x0F: "fence",
    0x13: "op_imm",
    0x17: "auipc",
    0x23: "store",
    0x33: "op",
    0x37: "lui",
    0x63: "branch",
    0x67: "jalr",
    0x6F: "jal",
    0x73: "system",
}


def num(text: str) -> int:
    text = (text or "0").strip()
    try:
        return int(text, 0)
    except ValueError:
        return int(text, 16)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("trace", type=Path)
    args = p.parse_args()

    counts = Counter()
    rows = 0
    last_cycle = 0

    with args.trace.open(newline="") as f:
        for r in csv.DictReader(f):
            rows += 1
            last_cycle = max(last_cycle, num(r.get("cycle", "0")))
            insn = num(r["insn"])
            counts[OPCODES.get(insn & 0x7F, "other")] += 1

    cpi = last_cycle / rows if rows else 0.0
    print("RV32IM trace summary")
    print("====================")
    print(f"retired : {rows}")
    print(f"cycles  : {last_cycle}")
    print(f"CPI     : {cpi:.4f}")
    print("\nInstruction mix:")
    for kind, count in counts.most_common():
        pct = (100.0 * count / rows) if rows else 0.0
        print(f"  {kind:10s} {count:8d}  {pct:6.2f}%")


if __name__ == "__main__":
    main()
