#!/usr/bin/env python3
from __future__ import print_function
import csv, os, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
R=os.path.join(ROOT,'results','milestone4')

def one(name):
    p=os.path.join(R,name)
    if not os.path.exists(p): return None
    with open(p,'r') as f:
        rows=list(csv.DictReader(f))
    return rows[0] if rows else None

def ints(row):
    if row is None: return None
    out={}
    for k,v in row.items():
        try: out[k]=int(v)
        except Exception:
            try: out[k]=float(v)
            except Exception: out[k]=v
    return out

m=ints(one('milestone4_summary.csv'))
e=ints(one('events_dhrystone.csv'))
if m is None:
    print('Run: python scripts/run_milestone4.py --require-rtl')
    sys.exit(1)
print('='*96)
print('MILESTONE 4 - FULL-WORKLOAD GAP ANALYSIS')
print('='*96)
print('model cycles              : {}'.format(m.get('cycles')))
print('RTL cycles                : {}'.format(m.get('rtl_cycles','n/a')))
if 'rtl_cycles' in m:
    print('cycle delta (model-RTL)   : {:+d}'.format(int(m['cycles'])-int(m['rtl_cycles'])))
print('model vs RTL I$ accesses  : {} vs {}'.format(m.get('icache_accesses'),m.get('rtl_icache_accesses','n/a')))
print('model vs RTL I$ misses    : {} vs {}'.format(m.get('icache_misses'),m.get('rtl_icache_misses','n/a')))
print('model vs RTL D$ accesses  : {} vs {}'.format(m.get('dcache_accesses'),m.get('rtl_dcache_accesses','n/a')))
print('model vs RTL D$ misses    : {} vs {}'.format(m.get('dcache_misses'),m.get('rtl_dcache_misses','n/a')))
if e:
    print('\nRTL EVENT COUNTERS')
    keys=['load_use_hazard_raw','load_use_hazard_effective','div_stall_hazard_raw','div_stall_hazard_effective',
          'if_stall_cycles','mem_stall_cycles','if_mem_overlap_cycles','loaduse_pipe_overlap_cycles','div_pipe_overlap_cycles',
          'icache_access_during_loaduse','icache_access_during_divstall','branch_redirect_events','jump_redirect_events','system_stop_cycles']
    for k in keys:
        if k in e: print('  {:34s} {}'.format(k,e[k]))
    print('\nMODEL COUNTERS TO CHECK')
    print('  load-use stalls                   {}'.format(m.get('load_use_stalls')))
    print('  divider stalls                    {}'.format(m.get('divider_stalls')))
    print('  branch redirect stalls            {}'.format(m.get('branch_stalls')))
    print('  jump redirect stalls              {}'.format(m.get('jump_stalls')))
    replay_gap=int(m.get('rtl_icache_accesses',0))-int(m.get('icache_accesses',0))
    print('\nI$ hit/access replay gap            {}'.format(replay_gap))
    hz=int(e.get('icache_access_during_loaduse',0))+int(e.get('icache_access_during_divstall',0))
    print('RTL accesses during load/div hold  {}'.format(hz))
    print('difference                          {:+d}'.format(replay_gap-hz))
print('\nDo not calibrate from the final cycle delta alone. Use the event counters and retirement trace to identify an overlap or hazard rule that generalizes.')
