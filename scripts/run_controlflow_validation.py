#!/usr/bin/env python3
from __future__ import print_function

import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PYTHON = sys.executable


def run(args):
    print('\n+ ' + ' '.join(args))
    return subprocess.call(args, cwd=ROOT)


def main():
    print('=' * 88)
    print('RV32IM CONTROL-FLOW PERFORMANCE CORRELATION')
    print('=' * 88)
    if run([PYTHON, os.path.join('scripts', 'run_milestone3c.py'), '--require-rtl']) != 0:
        return 1
    if run([PYTHON, os.path.join('scripts', 'run_milestone3d.py'), '--require-rtl']) != 0:
        return 1
    print('\nPASS: conditional branch + JAL/JALR directed correlation completed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
