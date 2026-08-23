#!/usr/bin/env python3
from __future__ import print_function

import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def run(cmd):
    print('\n+ ' + ' '.join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def main():
    print('=' * 88)
    print('MILESTONE 3B - CALIBRATED IF-STAGE + I/D-CACHE CORRELATION')
    print('=' * 88)

    # The user should extract the real VCS result ZIP at project root first.
    run([sys.executable, os.path.join('scripts', 'run_milestone3.py'), '--require-rtl'])

    fetch_a = os.path.join(ROOT, 'results', 'milestone3', 'fetch_icache_linear.csv')
    fetch_b = os.path.join(ROOT, 'results', 'milestone3', 'fetch_split_cache.csv')
    if os.path.exists(fetch_a) and os.path.exists(fetch_b):
        run([sys.executable, os.path.join('scripts', 'analyze_icache_fetch.py')])

    print('\n' + '=' * 88)
    print('MILESTONE 3B TARGET')
    print('=' * 88)
    print('dcache_repeat      : 17 cycles, D$ 2 access / 1 hit / 1 miss / 0 wb')
    print('dcache_cache_test  : 48 cycles, D$ 5 access / 2 hit / 3 miss / 2 wb')
    print('icache_linear      : 98 cycles, I$ 14 access / 2 hit / 12 miss')
    print('split_cache        : 139 cycles, I$ 48 access / 35 hit / 13 miss; D$ 3 miss / 2 wb')
    print('\nIf all four rows PASS, Milestone 3B is complete.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
