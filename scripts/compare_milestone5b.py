#!/usr/bin/env python3
from __future__ import print_function
import csv, os, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
PRED=os.path.join(ROOT,'results','milestone5','sensitivity_sweep.csv')
RTL=os.path.join(ROOT,'results','milestone5b','milestone5b_vcs_summary.csv')

def main():
    if not os.path.exists(PRED):
        raise RuntimeError('Missing sensitivity predictions; run python scripts/run_sensitivity_sweep.py')
    if not os.path.exists(RTL):
        raise RuntimeError('Missing Milestone 5B VCS summary. Extract RV32IM_VCS_Milestone5B_Results.zip at the project root.')
    pred={r['name']:r for r in csv.DictReader(open(PRED))}
    rtl=list(csv.DictReader(open(RTL)))
    print('='*116)
    print('MILESTONE 5B - MODEL-GUIDED CACHE OPTIMIZATION VALIDATION')
    print('='*116)
    print('{:10s} {:>5s} {:>5s} {:>11s} {:>11s} {:>9s} {:>10s} {:>8s}'.format('case','I$','D$','model','RTL','delta','reduction','status'))
    print('-'*116)
    allpass=True
    for r in rtl:
        p=pred[r['name']]
        status=r['status'];allpass=allpass and status=='PASS'
        print('{:10s} {:5s} {:5s} {:11s} {:11s} {:+9d} {:>9.3f}% {:>8s}'.format(r['name'],r['icache_lines'],r['dcache_lines'],r['model_cycles'],r['rtl_cycles'],int(r['cycle_delta']),float(p['cycle_reduction_pct']),status))
    print('\nRESULT: {}'.format('PASS - selected optimization predictions validated in RTL.' if allpass else 'MEASURE - inspect mismatched configurations before making optimization claims.'))
    return 0 if allpass else 1
if __name__=='__main__':sys.exit(main())
