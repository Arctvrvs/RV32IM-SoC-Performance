#!/usr/bin/env python3
from __future__ import print_function

import csv
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BUILD = os.path.join(ROOT, 'build')
WORKLOAD = os.path.join(ROOT, 'workloads', 'milestone4')
RESULTS = os.path.join(ROOT, 'results', 'milestone6')
REFERENCE = os.path.join(ROOT, 'reference', 'milestone6b')

KEYS = {
    'retired': 'retired',
    'predicted cycles': 'cycles',
    'I-cache accesses': 'icache_accesses',
    'I-cache hits': 'icache_hits',
    'I-cache misses': 'icache_misses',
    'D-cache accesses': 'dcache_accesses',
    'D-cache hits': 'dcache_hits',
    'D-cache misses': 'dcache_misses',
    'D-cache writebacks': 'dcache_writebacks',
    'I$/D$ overlap cycles': 'cache_overlap_cycles',
    'net cache stall cycles': 'net_cache_stalls',
}


def run(cmd, capture=False):
    if capture:
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, universal_newlines=True)
        out, _ = p.communicate()
        if p.returncode != 0:
            print(out)
            raise subprocess.CalledProcessError(p.returncode, cmd)
        return out
    subprocess.check_call(cmd, cwd=ROOT)
    return ''


def exe_path():
    choices = [
        os.path.join(BUILD, 'Release', 'rv32im_model.exe'),
        os.path.join(BUILD, 'rv32im_model.exe'),
        os.path.join(BUILD, 'rv32im_model'),
    ]
    for p in choices:
        if os.path.exists(p):
            return p
    raise RuntimeError('rv32im_model not found')


def parse(text):
    d = {}
    for line in text.splitlines():
        if ':' not in line:
            continue
        k, v = line.split(':', 1)
        k = k.strip()
        if k in KEYS:
            m = re.search(r'-?\d+', v)
            if m:
                d[KEYS[k]] = int(m.group(0))
    return d


def simulate(exe, name, ilines, dlines, latency, family):
    imem = os.path.join(WORKLOAD, 'dhrystone_imem.hex')
    dmem = os.path.join(WORKLOAD, 'dhrystone_dmem.hex')
    cmd = [exe, imem, '--dmem-hex', dmem, '--enable-caches',
           '--icache-lines', str(ilines), '--dcache-lines', str(dlines),
           '--memory-latency', str(latency), '--max-insns', '1000000']
    st = parse(run(cmd, capture=True))
    st.update({
        'name': name,
        'family': family,
        'icache_lines': ilines,
        'dcache_lines': dlines,
        'memory_latency': latency,
        # Data-array capacity proxy only. Tags/valid/dirty metadata are excluded.
        'cache_data_bytes': 4 * (ilines + dlines),
    })
    st['cpi'] = st['cycles'] / float(st['retired'])
    st['icache_hit_rate'] = 100.0 * st['icache_hits'] / float(st['icache_accesses'] or 1)
    st['dcache_hit_rate'] = 100.0 * st['dcache_hits'] / float(st['dcache_accesses'] or 1)
    return st


def pareto(rows):
    out = []
    for a in rows:
        dominated = False
        for b in rows:
            if a is b:
                continue
            no_worse = (b['cache_data_bytes'] <= a['cache_data_bytes'] and
                        b['cycles'] <= a['cycles'])
            strict = (b['cache_data_bytes'] < a['cache_data_bytes'] or
                      b['cycles'] < a['cycles'])
            if no_worse and strict:
                dominated = True
                break
        if not dominated:
            out.append(a)
    return sorted(out, key=lambda r: (r['cache_data_bytes'], r['cycles']))


def write_csv(path, rows, fields):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


def main():
    if not os.path.isdir(RESULTS):
        os.makedirs(RESULTS)
    if not os.path.isdir(REFERENCE):
        os.makedirs(REFERENCE)

    run(['cmake', '-S', '.', '-B', 'build', '-DRV32IM_BUILD_SYSTEMC=OFF'])
    run(['cmake', '--build', 'build', '--config', 'Release'])
    exe = exe_path()

    rows = []

    # Full cache-capacity grid at the calibrated backing latency.
    sizes = [32, 64, 128, 256, 512]
    for i in sizes:
        for d in sizes:
            name = 'I{}D{}L3'.format(i, d)
            print('CACHE GRID {:12s} I$={} D$={} LAT=3'.format(name, i, d))
            rows.append(simulate(exe, name, i, d, 3, 'cache_grid'))

    # Technology / memory-system latency sensitivity at baseline caches.
    for lat in [1, 2, 4, 5, 8, 12]:
        name = 'I64D64L{}'.format(lat)
        print('LATENCY    {:12s} I$=64 D$=64 LAT={}'.format(name, lat))
        rows.append(simulate(exe, name, 64, 64, lat, 'latency_sweep'))

    # Mixed capacity+latency points exercise interaction behavior.
    mixed = [
        (128, 64, 2),
        (256, 64, 2),
        (256, 128, 2),
        (256, 256, 2),
        (512, 64, 2),
        (256, 256, 5),
    ]
    for i, d, lat in mixed:
        name = 'I{}D{}L{}'.format(i, d, lat)
        print('MIXED      {:12s} I$={} D$={} LAT={}'.format(name, i, d, lat))
        rows.append(simulate(exe, name, i, d, lat, 'mixed'))

    # Remove exact duplicate configs while preserving first occurrence.
    unique = []
    seen = set()
    for r in rows:
        key = (r['icache_lines'], r['dcache_lines'], r['memory_latency'])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    rows = unique

    base = next(r for r in rows
                if r['icache_lines'] == 64 and r['dcache_lines'] == 64 and r['memory_latency'] == 3)
    base_bytes = base['cache_data_bytes']
    for r in rows:
        r['cycle_delta_vs_base'] = r['cycles'] - base['cycles']
        r['cycle_reduction_pct'] = 100.0 * (base['cycles'] - r['cycles']) / float(base['cycles'])
        r['speedup_vs_base'] = base['cycles'] / float(r['cycles'])
        r['extra_cache_data_bytes'] = r['cache_data_bytes'] - base_bytes
        if r['extra_cache_data_bytes'] > 0:
            r['cycles_saved_per_added_byte'] = (base['cycles'] - r['cycles']) / float(r['extra_cache_data_bytes'])
        else:
            r['cycles_saved_per_added_byte'] = ''

    cache_rows = [r for r in rows if r['family'] == 'cache_grid']
    frontier = pareto(cache_rows)
    for r in rows:
        r['pareto_cache_grid'] = 'yes' if r in frontier else 'no'

    fields = [
        'name', 'family', 'icache_lines', 'dcache_lines', 'memory_latency',
        'cache_data_bytes', 'extra_cache_data_bytes', 'pareto_cache_grid',
        'retired', 'cycles', 'cpi', 'cycle_delta_vs_base', 'cycle_reduction_pct',
        'speedup_vs_base', 'cycles_saved_per_added_byte',
        'icache_accesses', 'icache_hits', 'icache_misses', 'icache_hit_rate',
        'dcache_accesses', 'dcache_hits', 'dcache_misses', 'dcache_hit_rate',
        'dcache_writebacks', 'cache_overlap_cycles', 'net_cache_stalls'
    ]
    sweep_csv = os.path.join(RESULTS, 'design_space.csv')
    write_csv(sweep_csv, rows, fields)

    frontier_csv = os.path.join(RESULTS, 'cache_pareto_frontier.csv')
    write_csv(frontier_csv, frontier, fields)

    # Hard validation points: latency-only and mixed capacity+latency.
    selected_keys = [
        (64, 64, 1),
        (64, 64, 5),
        (256, 64, 2),
        (256, 256, 5),
    ]
    selected = []
    for key in selected_keys:
        selected.append(next(r for r in rows if
                             (r['icache_lines'], r['dcache_lines'], r['memory_latency']) == key))
    ref_csv = os.path.join(REFERENCE, 'selected_model_predictions.csv')
    write_csv(ref_csv, selected, fields)

    ranked = sorted(rows, key=lambda r: r['cycles'])
    efficiency = sorted(
        [r for r in cache_rows if isinstance(r['cycles_saved_per_added_byte'], float) and
         r['cycle_reduction_pct'] > 0],
        key=lambda r: r['cycles_saved_per_added_byte'], reverse=True)

    report = os.path.join(RESULTS, 'design_space_report.txt')
    with open(report, 'w') as f:
        f.write('RV32IM Milestone 6A - Dhrystone design-space exploration\n')
        f.write('=' * 86 + '\n')
        f.write('Calibrated baseline: I$64 D$64 LAT3 = {} cycles, CPI {:.6f}\n'.format(
            base['cycles'], base['cpi']))
        f.write('Cache-size cost uses DATA-ARRAY BYTES ONLY (4 bytes/line); tags/metadata/timing/energy excluded.\n\n')
        f.write('CACHE-CAPACITY PARETO FRONTIER (LAT=3)\n')
        for r in frontier:
            f.write('I${:<4d} D${:<4d} data={:<5d}B cycles={:<9d} reduction={:7.3f}% speedup={:.4f}x\n'.format(
                r['icache_lines'], r['dcache_lines'], r['cache_data_bytes'], r['cycles'],
                r['cycle_reduction_pct'], r['speedup_vs_base']))
        f.write('\nBEST CYCLES-SAVED PER ADDED DATA-ARRAY BYTE VS BASELINE\n')
        for r in efficiency[:8]:
            f.write('I${:<4d} D${:<4d} +{:>4d}B -> save {:>8d} cycles ({:7.3f}%), {:8.2f} cycles/B\n'.format(
                r['icache_lines'], r['dcache_lines'], r['extra_cache_data_bytes'],
                base['cycles'] - r['cycles'], r['cycle_reduction_pct'],
                r['cycles_saved_per_added_byte']))
        f.write('\nMEMORY-LATENCY SENSITIVITY (I$64/D$64)\n')
        lat_rows = sorted([r for r in rows if r['family'] == 'latency_sweep'] + [base],
                          key=lambda r: r['memory_latency'])
        for r in lat_rows:
            f.write('LAT={:<2d} cycles={:<9d} reduction={:8.3f}% speedup={:.4f}x\n'.format(
                r['memory_latency'], r['cycles'], r['cycle_reduction_pct'], r['speedup_vs_base']))
        f.write('\nSELECTED MILESTONE 6B RTL VALIDATION POINTS\n')
        for r in selected:
            f.write('{:12s} I${:<4d} D${:<4d} LAT={:<2d} cycles={:<9d} I$miss={:<7d} D$miss={:<6d} D$wb={}\n'.format(
                r['name'], r['icache_lines'], r['dcache_lines'], r['memory_latency'],
                r['cycles'], r['icache_misses'], r['dcache_misses'], r['dcache_writebacks']))
        f.write('\nNOTE: 6A is model-driven DSE. Only previously validated points and future 6B VCS points are RTL-validated.\n')

    print('\n' + '=' * 100)
    print('MILESTONE 6A SUMMARY')
    print('=' * 100)
    print('Baseline : {} cycles'.format(base['cycles']))
    print('Best DSE : {}  {} cycles ({:.3f}% reduction, {:.3f}x speedup)'.format(
        ranked[0]['name'], ranked[0]['cycles'], ranked[0]['cycle_reduction_pct'], ranked[0]['speedup_vs_base']))
    print('\nPareto cache points:')
    for r in frontier:
        print('  I${:<4d} D${:<4d} {:>5d}B  {:>9d} cycles  {:7.3f}% reduction'.format(
            r['icache_lines'], r['dcache_lines'], r['cache_data_bytes'], r['cycles'], r['cycle_reduction_pct']))
    print('\n6B frozen validation targets:')
    for r in selected:
        print('  {:12s} cycles={} I$miss={} D$miss={} D$wb={}'.format(
            r['name'], r['cycles'], r['icache_misses'], r['dcache_misses'], r['dcache_writebacks']))
    print('\nCSV     : ' + sweep_csv)
    print('Pareto  : ' + frontier_csv)
    print('Report  : ' + report)
    print('6B ref  : ' + ref_csv)
    return 0


if __name__ == '__main__':
    sys.exit(main())
