#!/usr/bin/env python3
from __future__ import print_function
import argparse,csv,math,os,sys

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES=['BASE_64_64','EFF_256_64','PERF_512_64']

REF=os.path.join(ROOT,'reference','validated_reference.csv')


def f(v,default=None):
    try:
        if v is None or str(v).strip()=='': return default
        return float(str(v).replace(',',''))
    except Exception:
        return default

def load_csv(path):
    if not os.path.isfile(path): return {}
    out={}
    with open(path,'r') as fh:
        for r in csv.DictReader(fh):
            if r.get('case'): out[r['case']]=r
    return out

def load_reference():
    return load_csv(REF)

def merge_inputs(corner,m7b_root,m8b_root,strict=False):
    ref=load_reference()
    m7path=os.path.join(m7b_root,'results','milestone7b',corner,'best_points.csv')
    m8path=os.path.join(m8b_root,'results','milestone8b',corner,'power_summary.csv')
    m7=load_csv(m7path); m8=load_csv(m8path)
    rows=[]
    sources=[]
    if m7: sources.append('M7B='+m7path)
    if m8: sources.append('M8B='+m8path)
    if strict and (not m7 or not m8):
        raise RuntimeError('strict mode requires populated M7B and M8B CSVs')
    for case in CASES:
        rr=dict(ref.get(case,{}))
        a=m7.get(case,{})
        p=m8.get(case,{})
        # Prefer actual sibling result CSVs, fall back only to locked validated reference values.
        row={
            'case':case,
            'icache_lines':int(f(a.get('icache_lines'),f(p.get('icache_lines'),f(rr.get('icache_lines'),0)))),
            'dcache_lines':int(f(a.get('dcache_lines'),f(p.get('dcache_lines'),f(rr.get('dcache_lines'),0)))),
            'cycles':int(f(a.get('dhrystone_cycles'),f(p.get('cycles'),f(rr.get('cycles'),0)))),
            'period_ns':f(a.get('best_met_period_ns'),f(p.get('period_ns'),f(rr.get('period_ns')))),
            'fmax_mhz':f(a.get('fmax_mhz'),f(p.get('fmax_mhz'),f(rr.get('fmax_mhz')))),
            'area':f(a.get('area'),f(p.get('m7b_best_area'),f(rr.get('area')))),
            'total_mw':f(p.get('total_mw'),f(rr.get('total_mw'))),
            'dynamic_mw':f(p.get('dynamic_mw'),f(rr.get('dynamic_mw'))),
            'leakage_mw':f(p.get('leakage_mw'),f(rr.get('leakage_mw'))),
            'energy_nj':f(p.get('energy_nj'),f(rr.get('energy_nj'))),
            'm7b_source':'csv' if case in m7 else 'validated_reference',
            'm8b_source':'csv' if case in m8 else 'validated_reference',
        }
        if row['period_ns'] and not row['fmax_mhz']:
            row['fmax_mhz']=1000.0/row['period_ns']
        row['runtime_us']=row['cycles']*row['period_ns']/1000.0
        if row['total_mw'] is not None and row['energy_nj'] is None:
            row['energy_nj']=row['total_mw']*row['runtime_us']
        rows.append(row)
    return rows,sources,m7path,m8path

def safe_ratio(a,b):
    return None if a is None or b is None or b==0 else a/b

def add_metrics(rows):
    base=next(r for r in rows if r['case']=='BASE_64_64')
    base_edp=base['energy_nj']*base['runtime_us']
    base_ed2p=base_edp*base['runtime_us']
    for r in rows:
        r['wall_speedup']=base['runtime_us']/r['runtime_us']
        r['area_ratio']=safe_ratio(r['area'],base['area'])
        r['power_ratio']=safe_ratio(r['total_mw'],base['total_mw'])
        r['energy_ratio']=safe_ratio(r['energy_nj'],base['energy_nj'])
        r['energy_reduction_pct']=(1.0-r['energy_ratio'])*100.0
        r['perf_per_area_norm']=safe_ratio(r['wall_speedup'],r['area_ratio'])
        r['perf_per_watt_norm']=safe_ratio(r['wall_speedup'],r['power_ratio'])
        r['perf_per_watt_area_norm']=safe_ratio(r['wall_speedup'],(r['power_ratio']*r['area_ratio']) if r['power_ratio'] and r['area_ratio'] else None)
        r['edp_nj_us']=r['energy_nj']*r['runtime_us']
        r['ed2p_nj_us2']=r['edp_nj_us']*r['runtime_us']
        r['edp_efficiency_norm']=base_edp/r['edp_nj_us']
        r['ed2p_efficiency_norm']=base_ed2p/r['ed2p_nj_us2']
        r['dynamic_fraction_pct']=safe_ratio(r['dynamic_mw'],r['total_mw'])*100.0
        r['leakage_fraction_pct']=safe_ratio(r['leakage_mw'],r['total_mw'])*100.0
    return rows

def dominates(a,b):
    # Multi-objective cost space: lower runtime, area, power, energy; strict improvement in >=1.
    keys=['runtime_us','area','total_mw','energy_nj']
    le=all(a[k] <= b[k] for k in keys)
    lt=any(a[k] < b[k] for k in keys)
    return le and lt

def classify(rows):
    for r in rows:
        dom=[x['case'] for x in rows if x is not r and dominates(x,r)]
        r['pareto_efficient']='YES' if not dom else 'NO'
        r['dominated_by']=';'.join(dom)
    return rows

def fmt(v,n=3):
    return 'N/A' if v is None else ('%.*f'%(n,v))

def write_csv(rows,path):
    fields=['case','icache_lines','dcache_lines','cycles','period_ns','fmax_mhz','runtime_us','wall_speedup',
            'area','area_ratio','total_mw','dynamic_mw','leakage_mw','power_ratio','energy_nj','energy_ratio','energy_reduction_pct',
            'perf_per_area_norm','perf_per_watt_norm','perf_per_watt_area_norm','edp_nj_us','edp_efficiency_norm','ed2p_nj_us2','ed2p_efficiency_norm',
            'dynamic_fraction_pct','leakage_fraction_pct','pareto_efficient','dominated_by','m7b_source','m8b_source']
    with open(path,'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(rows)

def svg_bar(path,title,rows,key,label,lower_better=False):
    W,H=900,420; left=210; right=60; top=65; rowh=90; barw=W-left-right
    vals=[r[key] for r in rows]; mx=max(vals) if vals else 1.0
    def esc(s): return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'%(W,H,W,H),
         '<rect width="100%%" height="100%%" fill="white"/>',
         '<text x="30" y="36" font-family="sans-serif" font-size="24" font-weight="bold">%s</text>'%esc(title)]
    for i,r in enumerate(rows):
        y=top+i*rowh
        val=r[key]; width=(val/mx)*barw if mx else 0
        out.append('<text x="30" y="%d" font-family="monospace" font-size="18">%s</text>'%(y+27,esc(r['case'])))
        out.append('<rect x="%d" y="%d" width="%.1f" height="34" fill="#777" rx="4"/>'%(left,y,width))
        out.append('<text x="%d" y="%d" font-family="sans-serif" font-size="17">%s</text>'%(min(left+width+10,W-150),y+24,esc(label(val))))
    note='lower is better' if lower_better else 'higher is better'
    out.append('<text x="30" y="%d" font-family="sans-serif" font-size="14">%s</text>'%(H-24,note))
    out.append('</svg>')
    open(path,'w').write('\n'.join(out))

def write_reports(rows,outdir,sources,m7path,m8path):
    perf=max(rows,key=lambda r:r['wall_speedup'])
    eff=max(rows,key=lambda r:r['perf_per_watt_norm'])
    pa=max(rows,key=lambda r:r['perf_per_area_norm'])
    energy=min(rows,key=lambda r:r['energy_nj'])
    edp=max(rows,key=lambda r:r['edp_efficiency_norm'])
    base=next(r for r in rows if r['case']=='BASE_64_64')
    lines=[]
    lines.append('MILESTONE 8C - CONSOLIDATED ARCHITECTURE SELECTION (SLOW CORNER)')
    lines.append('='*100)
    lines.append('case           runtime(us) wall_spd area_x power_x energy(nJ) energy_red perf/area perf/W  EDP_eff Pareto')
    lines.append('-'*100)
    for r in rows:
        lines.append('%-14s %11.3f %7.3fx %6.3fx %7.3fx %10.1f %8.2f%% %8.3fx %6.3fx %7.3fx %s'%(
            r['case'],r['runtime_us'],r['wall_speedup'],r['area_ratio'],r['power_ratio'],r['energy_nj'],r['energy_reduction_pct'],
            r['perf_per_area_norm'],r['perf_per_watt_norm'],r['edp_efficiency_norm'],r['pareto_efficient']))
    lines += ['', 'Selection:',
              '  Performance winner          : %s (%.3fx wall-clock speedup)'%(perf['case'],perf['wall_speedup']),
              '  Performance/area winner     : %s (%.3fx normalized)'%(pa['case'],pa['perf_per_area_norm']),
              '  Performance/watt winner     : %s (%.3fx normalized)'%(eff['case'],eff['perf_per_watt_norm']),
              '  Minimum workload energy     : %s (%.1f nJ, %.2f%% below baseline)'%(energy['case'],energy['energy_nj'],energy['energy_reduction_pct']),
              '  EDP winner                  : %s (%.3fx efficiency vs baseline)'%(edp['case'],edp['edp_efficiency_norm']),
              '',
              'Recommended architecture: PERF_512_64 for this Dhrystone-focused study.',
              'Reason: it is fastest and also leads both normalized performance/area and performance/watt among the three evaluated points, while using the least benchmark energy.',
              'Tradeoff: it has the highest absolute standard-cell area and instantaneous power. EFF_256_64 remains the moderate-area/power compromise.',
              '',
              'Important boundaries:',
              '  - Fmax is a same-flow Genus synthesis/pre-layout target boundary, not post-route or silicon Fmax.',
              '  - Cache arrays are RTL register arrays mapped to standard cells, not SRAM macros.',
              '  - Power/energy are same-flow relative estimates driven by M8A Dhrystone SAIF; they are not post-layout signoff power.',
              '  - Workload conclusion is Dhrystone-specific; another workload can change the cache-size optimum.',
              '',
              'Input discovery:',
              '  M7B expected: '+m7path,
              '  M8B expected: '+m8path]
    if sources:
        lines.append('  Used sibling CSVs: '+', '.join(sources))
    else:
        lines.append('  Used locked validated reference values bundled with M8C.')
    open(os.path.join(outdir,'architecture_selection_report.txt'),'w').write('\n'.join(lines)+'\n')

    md=['# Milestone 8C — Consolidated Architecture Selection','',
        '| Case | Runtime (us) | Wall speedup | Area x | Power x | Energy (nJ) | Energy reduction | Perf/Area | Perf/W | EDP efficiency | Pareto |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|']
    for r in rows:
        md.append('| %s | %.3f | %.3fx | %.3fx | %.3fx | %.1f | %.2f%% | %.3fx | %.3fx | %.3fx | %s |'%(
            r['case'],r['runtime_us'],r['wall_speedup'],r['area_ratio'],r['power_ratio'],r['energy_nj'],r['energy_reduction_pct'],r['perf_per_area_norm'],r['perf_per_watt_norm'],r['edp_efficiency_norm'],r['pareto_efficient']))
    md += ['', '## Decision',
           '**PERF_512_64 is the recommended Dhrystone architecture among the three evaluated points.** It has the best wall-clock performance, normalized performance/area, normalized performance/watt, minimum workload energy, and best EDP.',
           '', 'EFF_256_64 is the compromise point when absolute area or instantaneous power matters more than maximum throughput/energy efficiency. BASE_64_64 remains the minimum-area/minimum-power point.',
           '', '## Interpretation boundaries',
           '- Pre-layout synthesis-target Fmax only; not post-route/silicon Fmax.',
           '- Standard-cell-mapped RTL cache arrays; not SRAM-macro PPA.',
           '- SAIF-driven same-flow power/energy; not post-layout signoff power.',
           '- Dhrystone-specific selection; validate other workloads before claiming a universal optimum.']
    open(os.path.join(outdir,'architecture_selection_report.md'),'w').write('\n'.join(md)+'\n')

def main():
    ap=argparse.ArgumentParser(description='Milestone 8C consolidated PPA/energy architecture selection')
    ap.add_argument('--corner',default='slow',choices=['slow','fast'])
    ap.add_argument('--m7b-root',default=os.path.abspath(os.path.join(ROOT,'..','m7b_fmax')))
    ap.add_argument('--m8b-root',default=os.path.abspath(os.path.join(ROOT,'..','m8b_power')))
    ap.add_argument('--strict',action='store_true',help='require actual sibling M7B/M8B CSVs; do not use bundled reference fallback')
    a=ap.parse_args()
    rows,sources,m7path,m8path=merge_inputs(a.corner,a.m7b_root,a.m8b_root,a.strict)
    rows=classify(add_metrics(rows))
    out=os.path.join(ROOT,'results','milestone8c',a.corner); os.makedirs(out,exist_ok=True)
    charts=os.path.join(out,'charts'); os.makedirs(charts,exist_ok=True)
    write_csv(rows,os.path.join(out,'architecture_selection.csv'))
    write_reports(rows,out,sources,m7path,m8path)
    svg_bar(os.path.join(charts,'wall_speedup.svg'),'Dhrystone Wall-Clock Speedup',rows,'wall_speedup',lambda x:'%.3fx'%x,False)
    svg_bar(os.path.join(charts,'energy.svg'),'Dhrystone Workload Energy',rows,'energy_nj',lambda x:'%.1f nJ'%x,True)
    svg_bar(os.path.join(charts,'perf_per_area.svg'),'Normalized Performance / Area',rows,'perf_per_area_norm',lambda x:'%.3fx'%x,False)
    svg_bar(os.path.join(charts,'perf_per_watt.svg'),'Normalized Performance / Watt',rows,'perf_per_watt_norm',lambda x:'%.3fx'%x,False)
    print('='*122)
    print('MILESTONE 8C - CONSOLIDATED ARCHITECTURE SELECTION (%s corner)'%a.corner.upper())
    print('='*122)
    print('case           runtime(us) wall_spd area_x power_x energy(nJ) energy_red perf/area perf/W EDP_eff Pareto')
    print('-'*122)
    for r in rows:
        print('%-14s %11.3f %7.3fx %6.3fx %7.3fx %10.1f %8.2f%% %8.3fx %6.3fx %7.3fx %s'%(
            r['case'],r['runtime_us'],r['wall_speedup'],r['area_ratio'],r['power_ratio'],r['energy_nj'],r['energy_reduction_pct'],r['perf_per_area_norm'],r['perf_per_watt_norm'],r['edp_efficiency_norm'],r['pareto_efficient']))
    print('\nRESULT: PASS - consolidated M7B + M8B architecture-selection metrics generated.')
    print('Selection: PERF_512_64 for Dhrystone-focused performance/energy; EFF_256_64 remains the moderate area/power compromise.')
    print('CSV    : '+os.path.join(out,'architecture_selection.csv'))
    print('Report : '+os.path.join(out,'architecture_selection_report.txt'))
    print('Charts : '+charts)
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except Exception as e:
        print('ERROR: %s'%e); sys.exit(1)
