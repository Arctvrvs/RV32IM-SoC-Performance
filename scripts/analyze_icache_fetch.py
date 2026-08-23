#!/usr/bin/env python3
import csv
import os
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RES = os.path.join(ROOT, 'results', 'milestone3')
CASES = ['icache_linear', 'split_cache']


def read_csv(path):
    with open(path, 'r', newline='') as f:
        return list(csv.DictReader(f))


def h(x):
    return int(str(x), 0)


def main():
    print('=' * 100)
    print('MILESTONE 3B - I-CACHE FETCH-STREAM CHARACTERIZATION')
    print('=' * 100)
    missing = False
    for name in CASES:
        fetch_path = os.path.join(RES, 'fetch_' + name + '.csv')
        model_path = os.path.join(RES, 'model_' + name + '.csv')
        stats_path = os.path.join(RES, 'cache_' + name + '.csv')
        if not os.path.exists(fetch_path):
            print('\n{}: missing {}'.format(name, fetch_path))
            missing = True
            continue
        fetch = read_csv(fetch_path)
        model = read_csv(model_path) if os.path.exists(model_path) else []
        stats = read_csv(stats_path)[0] if os.path.exists(stats_path) else {}
        retired_pcs = [h(r['pc']) for r in model]
        fetch_pcs = [h(r['pc']) for r in fetch]
        misses = [r for r in fetch if int(r['miss'])]
        hits = [r for r in fetch if int(r['hit'])]

        print('\n{}'.format(name))
        print('-' * len(name))
        print('retired-PC model accesses : {}'.format(len(retired_pcs)))
        print('actual RTL I$ accesses    : {}'.format(len(fetch)))
        print('actual RTL I$ hits        : {}'.format(len(hits)))
        print('actual RTL I$ misses      : {}'.format(len(misses)))
        if stats:
            print('counter cross-check       : access={} hit={} miss={}'.format(
                stats.get('icache_accesses','?'), stats.get('icache_hits','?'), stats.get('icache_misses','?')))

        print('\n  #   cycle       PC        result   retired-PC?')
        print('  --  -----   ----------    ------   -----------')
        rc = Counter(retired_pcs)
        seen = Counter()
        for i, r in enumerate(fetch, 1):
            pc = h(r['pc'])
            seen[pc] += 1
            in_retired = 'yes' if pc in rc else 'NO'
            result = 'MISS' if int(r['miss']) else 'hit'
            print('  {:2d}  {:5d}   0x{:08x}    {:>4}       {}'.format(i, int(r['cycle']), pc, result, in_retired))

        miss_not_retired = [r for r in misses if h(r['pc']) not in rc]
        repeated = [(pc, cnt) for pc, cnt in Counter(fetch_pcs).items() if cnt > 1]
        print('\nmisses at non-retired PCs: {}'.format(
            ', '.join('0x{:08x}'.format(h(r['pc'])) for r in miss_not_retired) if miss_not_retired else 'none'))
        print('re-fetched PCs           : {}'.format(
            ', '.join('0x{:08x} x{}'.format(pc,cnt) for pc,cnt in sorted(repeated)) if repeated else 'none'))

    if missing:
        print('\nRun the Milestone 3B VCS bundle and extract its results ZIP into this project first.')
        return 2
    print('\nUse these exact access streams to implement the IF-stage cache model; do not tune from aggregate cycles alone.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
