#!/usr/bin/env python3
from __future__ import print_function

import argparse
import csv
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BUILD = os.path.join(ROOT, 'build')
RESULTS = os.path.join(ROOT, 'results', 'milestone3')

CASES = [
    {
        'name': 'dcache_repeat',
        'mode': 'validate',
        'program': os.path.join('workloads', 'milestone3', 'dcache_repeat.hex'),
        'args': ['--enable-dcache', '--dcache-lines', '4', '--memory-latency', '3'],
    },
    {
        'name': 'dcache_cache_test',
        'mode': 'validate',
        'program': os.path.join('workloads', 'milestone3', 'cache_test.hex'),
        'args': ['--enable-dcache', '--dcache-lines', '4', '--memory-latency', '3'],
    },
    {
        'name': 'icache_linear',
        'mode': 'validate',
        'program': os.path.join('workloads', 'milestone3', 'icache_linear.hex'),
        'args': ['--enable-icache', '--icache-lines', '4', '--memory-latency', '3'],
    },
    {
        'name': 'split_cache',
        'mode': 'validate',
        'program': os.path.join('workloads', 'milestone3', 'cache_test.hex'),
        'args': ['--enable-caches', '--icache-lines', '4', '--dcache-lines', '4', '--memory-latency', '3'],
    },
]

KEYS = {
    'retired': 'retired',
    'predicted cycles': 'cycles',
    'I-cache stalls': 'icache_stalls',
    'D-cache stalls': 'dcache_stalls',
    'I-cache accesses': 'icache_accesses',
    'I-cache hits': 'icache_hits',
    'I-cache misses': 'icache_misses',
    'D-cache accesses': 'dcache_accesses',
    'D-cache hits': 'dcache_hits',
    'D-cache misses': 'dcache_misses',
    'D-cache writebacks': 'dcache_writebacks',
    'AXI read transactions': 'axi_reads',
    'AXI write transactions': 'axi_writes',
}


def run(cmd, capture=False):
    print('\n+ ' + ' '.join(cmd))
    if capture:
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        out, _ = p.communicate()
        print(out, end='')
        if p.returncode != 0:
            raise subprocess.CalledProcessError(p.returncode, cmd)
        return out
    subprocess.check_call(cmd, cwd=ROOT)
    return ''


def executable_path():
    candidates = [
        os.path.join(BUILD, 'Release', 'rv32im_model.exe'),
        os.path.join(BUILD, 'Debug', 'rv32im_model.exe'),
        os.path.join(BUILD, 'rv32im_model.exe'),
        os.path.join(BUILD, 'rv32im_model'),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise RuntimeError('Could not find rv32im_model after build')


def parse_stats(text):
    result = {}
    for line in text.splitlines():
        if ':' not in line:
            continue
        left, right = line.split(':', 1)
        left = left.strip()
        if left not in KEYS:
            continue
        m = re.search(r'-?\d+', right)
        if m:
            result[KEYS[left]] = int(m.group(0))
    return result


def read_trace(path):
    with open(path, 'r') as f:
        return list(csv.DictReader(f))


def arch_equal(model, rtl):
    """Compare committed architectural behavior.

    PC and instruction must always match. Register-write enable must match.
    rd/wdata are only architecturally meaningful when reg_write is asserted;
    for stores/branches/system instructions those trace fields are don't-care.
    """
    if len(model) != len(rtl):
        return False

    for a, b in zip(model, rtl):
        if a.get('pc', '').lower() != b.get('pc', '').lower():
            return False
        if a.get('insn', '').lower() != b.get('insn', '').lower():
            return False

        a_wr = a.get('reg_write', '').lower()
        b_wr = b.get('reg_write', '').lower()
        if a_wr != b_wr:
            return False

        if a_wr not in ('0', '', 'false'):
            if a.get('rd', '').lower() != b.get('rd', '').lower():
                return False
            if a.get('wdata', '').lower() != b.get('wdata', '').lower():
                return False

    return True


def read_cache_stats(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    out = {}
    for k, v in rows[0].items():
        try:
            out[k] = int(v)
        except Exception:
            out[k] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model-only', action='store_true')
    ap.add_argument('--require-rtl', action='store_true')
    args = ap.parse_args()

    if not args.model_only and not args.require_rtl:
        args.model_only = True

    if not os.path.isdir(RESULTS):
        os.makedirs(RESULTS)

    run(['cmake', '-S', '.', '-B', 'build', '-DRV32IM_BUILD_SYSTEMC=OFF'])
    run(['cmake', '--build', 'build', '--config', 'Release'])
    exe = executable_path()

    summary = []
    for case in CASES:
        name = case['name']
        model_trace = os.path.join(RESULTS, 'model_' + name + '.csv')
        cmd = [exe, os.path.join(ROOT, case['program']), '--trace', model_trace] + case['args']
        out = run(cmd, capture=True)
        stats = parse_stats(out)
        row = dict(case)
        row.update(stats)
        row['arch'] = 'WAIT'
        row['timing'] = 'WAIT'
        row['rtl_cycles'] = 0
        row['cycle_error'] = 0.0
        row['cache_stats'] = 'WAIT'

        if args.require_rtl:
            rtl_trace = os.path.join(RESULTS, 'rtl_' + name + '.csv')
            rtl_stats_path = os.path.join(RESULTS, 'cache_' + name + '.csv')
            if not os.path.exists(rtl_trace) or not os.path.exists(rtl_stats_path):
                raise RuntimeError('Missing RTL result(s) for ' + name + '. Extract the VCS results ZIP at the project root.')
            mr = read_trace(model_trace)
            rr = read_trace(rtl_trace)
            row['arch'] = 'PASS' if arch_equal(mr, rr) else 'FAIL'
            rtl_cycles = int(rr[-1]['cycle']) if rr else 0
            row['rtl_cycles'] = rtl_cycles
            model_cycles = row.get('cycles', 0)
            row['cycle_error'] = 0.0 if rtl_cycles == 0 else abs(model_cycles - rtl_cycles) * 100.0 / rtl_cycles
            if case['mode'] == 'validate':
                row['timing'] = 'PASS' if model_cycles == rtl_cycles else 'FAIL'
            else:
                row['timing'] = 'MEASURE'

            rtlc = read_cache_stats(rtl_stats_path)
            expected_pairs = [
                ('icache_accesses', 'icache_accesses'), ('icache_hits', 'icache_hits'), ('icache_misses', 'icache_misses'),
                ('dcache_accesses', 'dcache_accesses'), ('dcache_hits', 'dcache_hits'), ('dcache_misses', 'dcache_misses'),
                ('dcache_writebacks', 'dcache_writebacks')
            ]
            same = True
            for mk, rk in expected_pairs:
                if mk in row and rk in rtlc and int(row[mk]) != int(rtlc[rk]):
                    same = False
            row['cache_stats'] = ('PASS' if same else ('MEASURE' if case['mode'] == 'measure' else 'FAIL'))

        summary.append(row)

    path = os.path.join(RESULTS, 'model_cache_summary.csv')
    fields = ['name','mode','retired','cycles','rtl_cycles','cycle_error','arch','timing','cache_stats',
              'icache_stalls','dcache_stalls','icache_accesses','icache_hits','icache_misses',
              'dcache_accesses','dcache_hits','dcache_misses','dcache_writebacks','axi_reads','axi_writes']
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in summary:
            w.writerow(r)

    print('\n' + '='*112)
    print('MILESTONE 3B CACHE + IF-FETCH SUMMARY')
    print('='*112)
    print('{:<20} {:<9} {:>7} {:>7} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8}'.format(
        'test','mode','model','rtl','I$miss','D$miss','D$wb','arch','timing','stats'))
    print('-'*112)
    for r in summary:
        print('{:<20} {:<9} {:>7} {:>7} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8}'.format(
            r['name'], r['mode'], r.get('cycles',0), r.get('rtl_cycles',0),
            r.get('icache_misses',0), r.get('dcache_misses',0), r.get('dcache_writebacks',0),
            r['arch'], r['timing'], r['cache_stats']))
    print('\nSummary CSV: ' + path)
    if args.model_only:
        print('\nModel predictions frozen. Run the Linux VCS cache-characterization bundle next.')
    else:
        print('\nAll four directed cache cases are now validation targets using the calibrated IF fetch-stream model.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
