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
RESULTS = os.path.join(ROOT, 'results', 'milestone4')
WORKLOAD = os.path.join(ROOT, 'workloads', 'milestone4')
REFERENCE = os.path.join(ROOT, 'reference', 'milestone4')

HISTORICAL_RTL = {
    # Canonical fresh retirement-trace target from Milestone 4A/4B.
    'cycles': 1365926,
    'icache_accesses': 368993,
    'icache_hits': 226574,
    'icache_misses': 142419,
    'dcache_accesses': 79394,
    'dcache_hits': 68740,
    'dcache_misses': 10654,
    'dcache_writebacks': 6056,
}
EXPECTED_X5 = 0x003fffff

KEYS = {
    'retired': 'retired',
    'predicted cycles': 'cycles',
    'ALU instructions': 'alu',
    'branches': 'branches',
    'branches taken': 'branches_taken',
    'jumps': 'jumps',
    'loads': 'loads',
    'stores': 'stores',
    'M-extension ops': 'mext',
    'base instruction cycles': 'base_cycles',
    'pipeline fill/drain': 'fill_drain',
    'load-use stalls': 'load_use_stalls',
    'taken-branch stalls': 'branch_stalls',
    'JAL/JALR redirect stalls': 'jump_stalls',
    'divider stalls': 'divider_stalls',
    'I-cache stalls': 'icache_stalls',
    'D-cache stalls': 'dcache_stalls',
    'I$/D$ overlap cycles': 'cache_overlap_cycles',
    'net cache stall cycles': 'net_cache_stalls',
    'I-cache accesses': 'icache_accesses',
    'I-cache hits': 'icache_hits',
    'I-cache misses': 'icache_misses',
    'I$ pipeline-hold replays': 'icache_pipeline_hold_replays',
    'D-cache accesses': 'dcache_accesses',
    'D-cache hits': 'dcache_hits',
    'D-cache misses': 'dcache_misses',
    'D-cache writebacks': 'dcache_writebacks',
    'D$ IF-stall replays': 'dcache_ifstall_replays',
    'AXI read transactions': 'axi_reads',
    'AXI write transactions': 'axi_writes',
}


def run(cmd, capture=False):
    print('\n+ ' + ' '.join(cmd))
    if capture:
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True)
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
        if k in KEYS:
            m = re.search(r'-?\d+', v)
            if m:
                out[KEYS[k]] = int(m.group(0))
    m = re.search(r'^x05\s*=\s*0x([0-9a-fA-F]+)', text, re.MULTILINE)
    if m:
        out['x5'] = int(m.group(1), 16)
    return out


def ival(x):
    return int(str(x), 0)


def arch_compare_stream(model_path, rtl_path):
    count = 0
    with open(model_path, 'r') as mf, open(rtl_path, 'r') as rf:
        mr = csv.DictReader(mf)
        rr = csv.DictReader(rf)
        while True:
            try:
                m = next(mr)
                m_end = False
            except StopIteration:
                m = None
                m_end = True
            try:
                r = next(rr)
                r_end = False
            except StopIteration:
                r = None
                r_end = True
            if m_end or r_end:
                if m_end and r_end:
                    return True, '{} retirements match'.format(count)
                return False, 'retirement-count mismatch after {}'.format(count)
            count += 1
            if ival(m['pc']) != ival(r['pc']) or ival(m['insn']) != ival(r['insn']) or \
               ival(m['reg_write']) != ival(r['reg_write']):
                return False, 'architectural mismatch at retirement {}'.format(count)
            if ival(m['reg_write']):
                if ival(m['rd']) != ival(r['rd']) or ival(m['wdata']) != ival(r['wdata']):
                    return False, 'register mismatch at retirement {}'.format(count)


def read_last_cycle(path):
    last = 0
    rows = 0
    with open(path, 'r') as f:
        for r in csv.DictReader(f):
            last = int(r['cycle'])
            rows += 1
    return last, rows


def read_one_csv(path):
    with open(path, 'r') as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else {}


def write_model_summary(stats):
    if not os.path.isdir(REFERENCE):
        os.makedirs(REFERENCE)
    fields = sorted(stats.keys())
    with open(os.path.join(REFERENCE, 'model_dhrystone_summary.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerow(stats)


def write_bottleneck_report(stats, rtl=None, events=None):
    path = os.path.join(RESULTS, 'bottleneck_report.txt')
    components = [
        ('I-cache miss stalls', stats.get('icache_stalls', 0)),
        ('base/retired work', stats.get('base_cycles', 0)),
        ('D-cache miss/writeback stalls', stats.get('dcache_stalls', 0)),
        ('I$/D$ overlap credit', -stats.get('cache_overlap_cycles', 0)),
        ('JAL/JALR redirects', stats.get('jump_stalls', 0)),
        ('taken-branch redirects', stats.get('branch_stalls', 0)),
        ('divider startup/drain', stats.get('divider_stalls', 0)),
        ('load-use hazards', stats.get('load_use_stalls', 0)),
        ('pipeline fill/drain', stats.get('fill_drain', 0)),
    ]
    components.sort(key=lambda x: x[1], reverse=True)
    total = float(stats.get('cycles', 0) or 1)
    with open(path, 'w') as f:
        f.write('RV32IM Milestone 4 - Dhrystone Bottleneck Attribution\n')
        f.write('='*72 + '\n')
        f.write('Model cycles  : {}\n'.format(stats.get('cycles', 0)))
        f.write('Retired       : {}\n'.format(stats.get('retired', 0)))
        f.write('Model CPI     : {:.6f}\n'.format(stats.get('cycles', 0) / float(stats.get('retired', 1))))
        f.write('Success x5    : 0x{:08x}\n\n'.format(stats.get('x5', 0)))
        f.write('MODEL CYCLE ATTRIBUTION\n')
        for name, cycles in components:
            f.write('  {:34s} {:9d}  {:6.2f}%\n'.format(name, cycles, 100.0*cycles/total))
        f.write('\nCACHE / AXI\n')
        f.write('  I$ access/hit/miss : {} / {} / {}\n'.format(stats.get('icache_accesses',0), stats.get('icache_hits',0), stats.get('icache_misses',0)))
        f.write('  D$ access/hit/miss : {} / {} / {}\n'.format(stats.get('dcache_accesses',0), stats.get('dcache_hits',0), stats.get('dcache_misses',0)))
        f.write('  D$ writebacks      : {}\n'.format(stats.get('dcache_writebacks',0)))
        f.write('  AXI reads/writes   : {} / {}\n'.format(stats.get('axi_reads',0), stats.get('axi_writes',0)))
        if rtl:
            f.write('\nFRESH RTL CORRELATION\n')
            f.write('  RTL cycles          : {}\n'.format(rtl.get('cycles',0)))
            f.write('  cycle delta          : {:+d}\n'.format(stats.get('cycles',0)-rtl.get('cycles',0)))
            if rtl.get('cycles',0):
                f.write('  absolute cycle error : {:.6f}%\n'.format(abs(stats.get('cycles',0)-rtl['cycles'])*100.0/rtl['cycles']))
            f.write('  RTL I$ a/h/m         : {} / {} / {}\n'.format(rtl.get('icache_accesses',0), rtl.get('icache_hits',0), rtl.get('icache_misses',0)))
            f.write('  RTL D$ a/h/m/wb      : {} / {} / {} / {}\n'.format(rtl.get('dcache_accesses',0), rtl.get('dcache_hits',0), rtl.get('dcache_misses',0), rtl.get('dcache_writebacks',0)))
        if events:
            f.write('\nRTL EVENT COUNTERS\n')
            for key in sorted(events):
                f.write('  {:34s} {}\n'.format(key, events[key]))
    return path


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

    imem = os.path.join(WORKLOAD, 'dhrystone_imem.hex')
    dmem = os.path.join(WORKLOAD, 'dhrystone_dmem.hex')
    model_trace = os.path.join(RESULTS, 'model_dhrystone.csv')
    cmd = [exe, imem, '--dmem-hex', dmem, '--trace', model_trace,
           '--enable-caches', '--icache-lines', '64', '--dcache-lines', '64',
           '--memory-latency', '3', '--max-insns', '1000000', '--dump-regs']
    out = run(cmd, capture=True)
    stats = parse_stats(out)
    if stats.get('x5') != EXPECTED_X5:
        raise RuntimeError('Dhrystone model signature failed: x5=0x{:08x}'.format(stats.get('x5',0)))
    write_model_summary(stats)

    hist_delta = stats['cycles'] - HISTORICAL_RTL['cycles']
    hist_err = abs(hist_delta) * 100.0 / HISTORICAL_RTL['cycles']

    print('\n' + '='*108)
    print('MILESTONE 4B - OVERLAP-AWARE DHRYSTONE FULL-WORKLOAD CORRELATION')
    print('='*108)
    print('model signature          : PASS (x5=0x{:08x})'.format(stats['x5']))
    print('model retired            : {}'.format(stats['retired']))
    print('model cycles             : {}'.format(stats['cycles']))
    print('fresh reference RTL cycles    : {}'.format(HISTORICAL_RTL['cycles']))
    print('fresh reference cycle delta   : {:+d} ({:.6f}%)'.format(hist_delta, hist_err))
    print('model I$ miss            : {}   reference RTL: {}'.format(stats['icache_misses'], HISTORICAL_RTL['icache_misses']))
    print('model D$ miss            : {}   reference RTL: {}'.format(stats['dcache_misses'], HISTORICAL_RTL['dcache_misses']))
    print('model D$ writeback       : {}    reference RTL: {}'.format(stats['dcache_writebacks'], HISTORICAL_RTL['dcache_writebacks']))
    print('model I$ access          : {}   reference RTL: {}   gap={:+d}'.format(stats['icache_accesses'], HISTORICAL_RTL['icache_accesses'], stats['icache_accesses']-HISTORICAL_RTL['icache_accesses']))
    print('model D$ access          : {}    reference RTL: {}    gap={:+d}'.format(stats['dcache_accesses'], HISTORICAL_RTL['dcache_accesses'], stats['dcache_accesses']-HISTORICAL_RTL['dcache_accesses']))

    rtl = None
    events = None
    arch = 'WAIT'
    timing = 'MEASURE'
    cache = 'MEASURE'
    if args.require_rtl:
        rtl_trace = os.path.join(RESULTS, 'rtl_dhrystone.csv')
        rtl_stats = os.path.join(RESULTS, 'cache_dhrystone.csv')
        rtl_events = os.path.join(RESULTS, 'events_dhrystone.csv')
        for p in (rtl_trace, rtl_stats, rtl_events):
            if not os.path.exists(p):
                raise RuntimeError('Missing fresh VCS result: {}. Extract RV32IM_VCS_Milestone4_Results.zip at the project root.'.format(p))
        ok, note = arch_compare_stream(model_trace, rtl_trace)
        arch = 'PASS' if ok else 'FAIL'
        rtl_cycles, rtl_retired = read_last_cycle(rtl_trace)
        rs = read_one_csv(rtl_stats)
        ev = read_one_csv(rtl_events)
        rtl = {'cycles': rtl_cycles, 'retired': rtl_retired}
        for k in ['icache_accesses','icache_hits','icache_misses','dcache_accesses','dcache_hits','dcache_misses','dcache_writebacks']:
            rtl[k] = int(rs.get(k, 0))
        events = {}
        for k,v in ev.items():
            try:
                events[k] = int(v)
            except Exception:
                events[k] = v
        timing = 'PASS' if stats['cycles'] == rtl_cycles else 'MEASURE'
        cache = 'PASS' if (stats['icache_accesses'] == rtl['icache_accesses'] and
                           stats['icache_hits'] == rtl['icache_hits'] and
                           stats['icache_misses'] == rtl['icache_misses'] and
                           stats['dcache_accesses'] == rtl['dcache_accesses'] and
                           stats['dcache_hits'] == rtl['dcache_hits'] and
                           stats['dcache_misses'] == rtl['dcache_misses'] and
                           stats['dcache_writebacks'] == rtl['dcache_writebacks']) else 'MEASURE'
        print('\nFRESH VCS RESULT')
        print('architectural            : {} ({})'.format(arch, note))
        print('RTL retired              : {}'.format(rtl_retired))
        print('RTL cycles               : {}'.format(rtl_cycles))
        print('model - RTL cycle delta  : {:+d}'.format(stats['cycles'] - rtl_cycles))
        print('cycle error              : {:.6f}%'.format(abs(stats['cycles']-rtl_cycles)*100.0/rtl_cycles if rtl_cycles else 0.0))
        print('RTL I$ a/h/m             : {} / {} / {}'.format(rtl['icache_accesses'],rtl['icache_hits'],rtl['icache_misses']))
        print('RTL D$ a/h/m/wb          : {} / {} / {} / {}'.format(rtl['dcache_accesses'],rtl['dcache_hits'],rtl['dcache_misses'],rtl['dcache_writebacks']))
        print('timing status            : {}'.format(timing))
        print('full cache-counter status : {}'.format(cache))
        print('model I$/D$ overlap      : {}'.format(stats.get('cache_overlap_cycles',0)))
        print('model I$ hold replays    : {}'.format(stats.get('icache_pipeline_hold_replays',0)))
        print('model D$ IF replays      : {}'.format(stats.get('dcache_ifstall_replays',0)))

    report = write_bottleneck_report(stats, rtl, events)
    print('\nBottleneck report: ' + report)

    summary_path = os.path.join(RESULTS, 'milestone4_summary.csv')
    row = dict(stats)
    row.update({'arch':arch,'timing':timing,'cache':cache,
                'reference_rtl_cycles':HISTORICAL_RTL['cycles'],
                'reference_cycle_delta':hist_delta,
                'reference_cycle_error_pct':'{:.8f}'.format(hist_err)})
    if rtl:
        row['rtl_cycles'] = rtl['cycles']; row['rtl_retired'] = rtl['retired']
        row['rtl_icache_accesses'] = rtl['icache_accesses']; row['rtl_icache_hits'] = rtl['icache_hits']; row['rtl_icache_misses'] = rtl['icache_misses']
        row['rtl_dcache_accesses'] = rtl['dcache_accesses']; row['rtl_dcache_hits'] = rtl['dcache_hits']; row['rtl_dcache_misses'] = rtl['dcache_misses']; row['rtl_dcache_writebacks'] = rtl['dcache_writebacks']
    with open(summary_path, 'w', newline='') as f:
        fields = sorted(row.keys()); w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerow(row)
    print('Summary CSV      : ' + summary_path)
    if args.model_only:
        print('\nMilestone 4B model-only target: 1,365,926 cycles and exact full cache counters. Use --require-rtl after extracting the real VCS result ZIP.')
    else:
        if arch == 'PASS' and timing == 'PASS' and cache == 'PASS':
            print('\nRESULT: PASS - Dhrystone architecture, cycles, and full I$/D$ counters correlate exactly.')
        else:
            print('\nUse: python scripts/analyze_milestone4_gaps.py')
    return 0

if __name__ == '__main__':
    sys.exit(main())
