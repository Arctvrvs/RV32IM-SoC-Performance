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
RESULTS = os.path.join(ROOT, 'results', 'milestone3d')

CASES = [
    ('jal_forward_link', 'validate', 'forward JAL with link-register write'),
    ('jal_backward_loop', 'validate', 'backward JAL x0 redirect plus calibrated branch exit'),
    ('jalr_forward', 'validate', 'register-indirect forward JALR redirect'),
    ('call_return', 'validate', 'JAL call + JALR return + JAL exit sequence'),
]

KEYS = {
    'retired': 'retired',
    'predicted cycles': 'cycles',
    'branches': 'branches',
    'branches taken': 'branches_taken',
    'jumps': 'jumps',
    'I-cache stalls': 'icache_stalls',
    'JAL/JALR redirect stalls': 'jump_stalls',
    'I-cache accesses': 'icache_accesses',
    'I-cache hits': 'icache_hits',
    'I-cache misses': 'icache_misses',
    'AXI read transactions': 'axi_reads',
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
    out = {}
    for line in text.splitlines():
        if ':' not in line:
            continue
        k, v = line.split(':', 1)
        k = k.strip()
        if k not in KEYS:
            continue
        m = re.search(r'-?\d+', v)
        if m:
            out[KEYS[k]] = int(m.group(0))
    return out


def read_trace(path):
    with open(path, 'r') as f:
        return list(csv.DictReader(f))


def ival(x):
    return int(str(x), 0)


def arch_equal(model, rtl):
    if len(model) != len(rtl):
        return False, 'retired model={} rtl={}'.format(len(model), len(rtl))
    for i, pair in enumerate(zip(model, rtl)):
        m, r = pair
        if ival(m['pc']) != ival(r['pc']) or ival(m['insn']) != ival(r['insn']) or ival(m['reg_write']) != ival(r['reg_write']):
            return False, 'mismatch at retirement {}'.format(i + 1)
        if ival(m['reg_write']):
            if ival(m['rd']) != ival(r['rd']) or ival(m['wdata']) != ival(r['wdata']):
                return False, 'register mismatch at retirement {}'.format(i + 1)
    return True, '{} retirements match'.format(len(model))


def read_one_csv(path):
    with open(path, 'r') as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else {}


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

    rows = []
    for name, mode, purpose in CASES:
        model_trace = os.path.join(RESULTS, 'model_' + name + '.csv')
        prog = os.path.join(ROOT, 'workloads', 'milestone3d', name + '.hex')
        out = run([exe, prog, '--trace', model_trace, '--enable-icache', '--icache-lines', '4', '--memory-latency', '3'], capture=True)
        row = {'name': name, 'mode': mode, 'purpose': purpose, 'arch': 'WAIT', 'timing': 'WAIT', 'stats': 'WAIT',
               'rtl_cycles': 0, 'cycle_error': 0.0, 'rtl_i_access': 0, 'rtl_i_hits': 0, 'rtl_i_misses': 0}
        row.update(parse_stats(out))

        if args.require_rtl:
            rtl_trace_path = os.path.join(RESULTS, 'rtl_' + name + '.csv')
            rtl_stats_path = os.path.join(RESULTS, 'cache_' + name + '.csv')
            if not os.path.exists(rtl_trace_path) or not os.path.exists(rtl_stats_path):
                raise RuntimeError('Missing RTL results for {}. Extract the VCS Milestone 3D results ZIP at the project root.'.format(name))
            mr = read_trace(model_trace)
            rr = read_trace(rtl_trace_path)
            ok, note = arch_equal(mr, rr)
            row['arch'] = 'PASS' if ok else 'FAIL'
            row['arch_note'] = note
            row['rtl_cycles'] = int(rr[-1]['cycle']) if rr else 0
            if row['rtl_cycles']:
                row['cycle_error'] = abs(row['cycles'] - row['rtl_cycles']) * 100.0 / row['rtl_cycles']
            rs = read_one_csv(rtl_stats_path)
            row['rtl_i_access'] = int(rs.get('icache_accesses', 0))
            row['rtl_i_hits'] = int(rs.get('icache_hits', 0))
            row['rtl_i_misses'] = int(rs.get('icache_misses', 0))
            row['timing'] = 'PASS' if row['cycles'] == row['rtl_cycles'] else 'FAIL'
            stats_ok = (row.get('icache_accesses',0) == row['rtl_i_access'] and
                        row.get('icache_hits',0) == row['rtl_i_hits'] and
                        row.get('icache_misses',0) == row['rtl_i_misses'])
            row['stats'] = 'PASS' if stats_ok else 'FAIL'
        rows.append(row)

    outcsv = os.path.join(RESULTS, 'model_jump_summary.csv')
    fields = ['name','mode','purpose','retired','branches','branches_taken','jumps','cycles','rtl_cycles','cycle_error','arch','timing','stats',
              'icache_stalls','icache_accesses','icache_hits','icache_misses','rtl_i_access','rtl_i_hits','rtl_i_misses','axi_reads']
    with open(outcsv, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for row in rows:
            w.writerow(row)

    print('\n' + '='*122)
    print('MILESTONE 3D - CALIBRATED JAL / JALR CALL-RETURN I-CACHE CORRELATION')
    print('='*122)
    print('{:<20} {:<8} {:>7} {:>7} {:>7} {:>8} {:>8} {:>8} {:>8} {:>8}'.format(
        'test','mode','model','rtl','M I$miss','R I$miss','arch','timing','stats','error'))
    print('-'*122)
    for r in rows:
        print('{:<20} {:<8} {:>7} {:>7} {:>7} {:>8} {:>8} {:>8} {:>8} {:>7.2f}%'.format(
            r['name'], r['mode'], r.get('cycles',0), r.get('rtl_cycles',0), r.get('icache_misses',0), r.get('rtl_i_misses',0),
            r['arch'], r['timing'], r['stats'], r.get('cycle_error',0.0)))
    print('\nSummary CSV: ' + outcsv)
    if args.model_only:
        print('\nCalibrated jump predictions generated. Use --require-rtl with the collected VCS results for exact validation.')
    else:
        all_pass = all(r['arch'] == 'PASS' and r['timing'] == 'PASS' and r['stats'] == 'PASS' for r in rows)
        print('\nRESULT: ' + ('PASS - all JAL/JALR directed cases correlate exactly.' if all_pass else 'FAIL - inspect the rows above.'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
