#!/usr/bin/env python3
"""Run the complete Milestone 2 calibrated pipeline-timing regression."""
from __future__ import print_function

import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
PYTHON = sys.executable


def run(script, *args):
    cmd = [PYTHON, os.path.join(ROOT, "scripts", script)] + list(args)
    print("\n" + "=" * 80)
    print("+ " + " ".join(cmd))
    print("=" * 80)
    return subprocess.call(cmd, cwd=ROOT)


def main():
    rc = run("run_validation_suite.py", "--require-rtl")
    if rc != 0:
        return rc
    rc = run("run_divider_characterization.py", "--require-rtl")
    if rc != 0:
        return rc

    print("\n" + "=" * 80)
    print("MILESTONE 2 COMPLETE")
    print("=" * 80)
    print("PASS: architectural correlation")
    print("PASS: 5-stage baseline timing")
    print("PASS: load-use timing")
    print("PASS: taken-branch timing")
    print("PASS: 8-stage pipelined DIV/REM timing (latency=8, II=1)")
    print("PASS: exact retirement-cycle correlation on all collected directed tests")
    print("\nNext milestone: cache/memory hierarchy performance modeling.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
