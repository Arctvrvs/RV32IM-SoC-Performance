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
RESULTS = os.path.join(ROOT, 'results', 'milestone5')

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
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True)
        out, _ = p.communicate()
        if p.returncode != 0:
            print(out)
            raise subprocess.CalledProcessError(p.returncode, cmd)
        return out
    subprocess.check_call(cmd, cwd=ROOT)
    return ''

def exe_path():
    for p in [os.path.join(BUILD,'Release','rv32im_model.exe'),
              os.path.join(BUILD,'rv32im_model.exe'),
              os.path.join(BUILD,'rv32im_model')]:
        if os.path.exists(p): return p
    raise RuntimeError('rv32im_model not found')

def parse(text):
    d={}
    for line in text.splitlines():
        if ':' not in line: continue
        k,v=line.split(':',1); k=k.strip()
        if k in KEYS:
            m=re.search(r'-?\d+',v)
            if m: d[KEYS[k]]=int(m.group(0))
    return d

def one(exe, name, ilines, dlines, latency):
    imem=os.path.join(WORKLOAD,'dhrystone_imem.hex')
    dmem=os.path.join(WORKLOAD,'dhrystone_dmem.hex')
    cmd=[exe,imem,'--dmem-hex',dmem,'--enable-caches',
         '--icache-lines',str(ilines),'--dcache-lines',str(dlines),
         '--memory-latency',str(latency),'--max-insns','1000000']
    st=parse(run(cmd,capture=True))
    st.update({'name':name,'icache_lines':ilines,'dcache_lines':dlines,'memory_latency':latency})
    st['cpi']=st['cycles']/float(st['retired'])
    st['icache_hit_rate']=100.0*(st['icache_accesses']-st['icache_misses'])/float(st['icache_accesses'] or 1)
    st['dcache_hit_rate']=100.0*(st['dcache_accesses']-st['dcache_misses'])/float(st['dcache_accesses'] or 1)
    return st

def main():
    if not os.path.isdir(RESULTS): os.makedirs(RESULTS)
    run(['cmake','-S','.','-B','build','-DRV32IM_BUILD_SYSTEMC=OFF'])
    run(['cmake','--build','build','--config','Release'])
    exe=exe_path()

    cases=[]
    for n in [16,32,64,128,256,512]:
        cases.append(('I${}'.format(n),n,64,3))
    for n in [16,32,128,256,512]:
        cases.append(('D${}'.format(n),64,n,3))
    for lat in [1,2,4,5,8,12]:
        cases.append(('LAT{}'.format(lat),64,64,lat))
    for i,d in [(128,128),(256,128),(128,256),(256,256)]:
        cases.append(('I{}D{}'.format(i,d),i,d,3))

    rows=[]
    for idx,(name,i,d,lat) in enumerate(cases,1):
        print('[{:02d}/{:02d}] {:10s} I$={} D$={} LAT={}'.format(idx,len(cases),name,i,d,lat))
        rows.append(one(exe,name,i,d,lat))

    base=next(r for r in rows if r['icache_lines']==64 and r['dcache_lines']==64 and r['memory_latency']==3)
    for r in rows:
        r['cycle_delta_vs_base']=r['cycles']-base['cycles']
        r['speedup_vs_base']=base['cycles']/float(r['cycles'])
        r['cycle_reduction_pct']=100.0*(base['cycles']-r['cycles'])/float(base['cycles'])

    out=os.path.join(RESULTS,'sensitivity_sweep.csv')
    fields=['name','icache_lines','dcache_lines','memory_latency','retired','cycles','cpi',
            'cycle_delta_vs_base','cycle_reduction_pct','speedup_vs_base',
            'icache_accesses','icache_misses','icache_hit_rate',
            'dcache_accesses','dcache_misses','dcache_hit_rate','dcache_writebacks',
            'cache_overlap_cycles','net_cache_stalls']
    with open(out,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,'') for k in fields})

    ranked=sorted(rows,key=lambda r:r['cycles'])
    report=os.path.join(RESULTS,'sensitivity_report.txt')
    with open(report,'w') as f:
        f.write('RV32IM Milestone 5A - Dhrystone sensitivity predictions\n')
        f.write('='*76+'\n')
        f.write('Baseline: I$64 D$64 LAT3 = {} cycles, CPI {:.6f}\n\n'.format(base['cycles'],base['cpi']))
        f.write('TOP PREDICTED CONFIGURATIONS\n')
        for r in ranked[:10]:
            f.write('{:10s} I${:<4d} D${:<4d} LAT={:<2d} cycles={:<9d} reduction={:7.3f}% speedup={:.4f}x\n'.format(
                r['name'],r['icache_lines'],r['dcache_lines'],r['memory_latency'],r['cycles'],r['cycle_reduction_pct'],r['speedup_vs_base']))
        f.write('\nNOTE: sensitivity results are model predictions until selected points are re-run in RTL/VCS.\n')
    print('\nBaseline cycles : {}'.format(base['cycles']))
    print('Best predicted  : {} cycles ({:.3f}% reduction)'.format(ranked[0]['cycles'],ranked[0]['cycle_reduction_pct']))
    print('CSV             : '+out)
    print('Report          : '+report)
    return 0

if __name__=='__main__':
    sys.exit(main())
