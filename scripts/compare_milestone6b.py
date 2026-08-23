#!/usr/bin/env python3
from __future__ import print_function
import csv, os, sys

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
REF=os.path.join(ROOT,'reference','milestone6b','selected_model_predictions.csv')
RTL=os.path.join(ROOT,'results','milestone6b','milestone6b_vcs_summary.csv')

def main():
    if not os.path.exists(RTL):
        print('Missing '+RTL)
        print('Extract RV32IM_VCS_Milestone6B_Results.zip at the project root first.')
        return 2
    refs={r['name']:r for r in csv.DictReader(open(REF))}
    rows=list(csv.DictReader(open(RTL)))
    print('='*124)
    print('MILESTONE 6B - MEMORY-LATENCY + CACHE-INTERACTION RTL VALIDATION')
    print('='*124)
    print('{:<14s} {:>4s} {:>4s} {:>4s} {:>11s} {:>11s} {:>8s} {:>10s} {:>8s}'.format(
        'case','I$','D$','LAT','model','RTL','delta','reduction','status'))
    print('-'*124)
    ok=True
    base=1365926
    for row in rows:
        name=row['name']; ref=refs.get(name)
        if ref is None:
            print('Unexpected RTL row: '+name);ok=False;continue
        mc=int(ref['cycles']); rc=int(row['rtl_cycles']); delta=mc-rc
        status=row.get('status','')
        reduction=100.0*(base-rc)/float(base)
        print('{:<14s} {:>4d} {:>4d} {:>4d} {:>11d} {:>11d} {:+8d} {:>9.3f}% {:>8s}'.format(
            name,int(ref['icache_lines']),int(ref['dcache_lines']),int(ref['memory_latency']),
            mc,rc,delta,reduction,status))
        if delta!=0 or status!='PASS':ok=False
    print()
    if ok and len(rows)==len(refs):
        print('RESULT: PASS - latency and mixed cache+latency predictions validated in RTL.')
        return 0
    print('RESULT: CHECK - inspect mismatched rows before extending the model.')
    return 1

if __name__=='__main__':sys.exit(main())
