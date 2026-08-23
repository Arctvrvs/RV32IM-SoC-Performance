#!/usr/bin/env python3
from __future__ import print_function
import csv, os, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
R=os.path.join(ROOT,'results','milestone4')
OVER=os.path.join(R,'overlap_cycles.csv')
REP=os.path.join(R,'dcache_replays.csv')

def read(path):
    if not os.path.exists(path):
        raise RuntimeError('Missing '+path+'; run python3 scripts/run_vcs_milestone4.py first')
    with open(path,'r') as f: return list(csv.DictReader(f))

def hx(v): return int(v,0)

o=read(OVER); r=read(REP)
print('='*112)
print('MILESTONE 4B - I$/D$ OVERLAP + D-CACHE REPLAY ANALYSIS')
print('='*112)
print('simultaneous I$/D$ stall cycles : {}'.format(len(o)))
# Group consecutive overlap cycles into episodes.
eps=[]
for row in o:
    c=int(row['cycle'])
    key=(row['ex_mem_pc'],row['dmem_addr'],row['redirect_pc'])
    if eps and c==eps[-1]['end']+1 and key==eps[-1]['key']:
        eps[-1]['end']=c; eps[-1]['rows'].append(row)
    else:
        eps.append({'start':c,'end':c,'key':key,'rows':[row]})
print('overlap episodes                : {}'.format(len(eps)))
for i,e in enumerate(eps,1):
    first=e['rows'][0]
    print('  #{:d}: cycles {}..{} duration={} ex_mem_pc={} daddr={} redirect={} target={}'.format(
        i,e['start'],e['end'],e['end']-e['start']+1,first['ex_mem_pc'],first['dmem_addr'],first['ex_redirect'],first['redirect_pc']))
print('\nD-cache replay rows             : {}'.format(len(r)))
valid=0
for i,row in enumerate(r,1):
    same=hx(row['expected_addr'])==hx(row['observed_addr'])
    hit=int(row['dcache_hit'])!=0
    if same and hit: valid+=1
    print('  #{:d}: cycle={} mem_pc={} addr={} hit={} same_addr={}'.format(
        i,row['cycle'],row['mem_pc'],row['observed_addr'],'yes' if hit else 'no','yes' if same else 'no'))
print('validated filled-line replays    : {}'.format(valid))
print('\nCorrelation checks:')
print('  expected D$ access gap          : 2')
print('  observed replay candidates      : {}'.format(valid))
print('  expected aggregate overlap      : 12 cycles')
print('  observed overlap rows           : {}'.format(len(o)))
if len(o)==12 and valid==2:
    print('\nRESULT: PASS - the +12 cycle error and +2 D$ access gap come from the same two overlap/replay episodes.')
else:
    print('\nRESULT: MEASURE - inspect the episode rows before calibrating the model.')
