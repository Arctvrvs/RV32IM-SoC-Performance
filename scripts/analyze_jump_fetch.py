#!/usr/bin/env python3
from __future__ import print_function

import csv
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RESULTS = os.path.join(ROOT, 'results', 'milestone3d')
CASES = ['jal_forward_link','jal_backward_loop','jalr_forward','call_return']


def rows(path):
    with open(path, 'r') as f:
        return list(csv.DictReader(f))


def sx(value, bits):
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def jal_target(pc, insn):
    if (insn & 0x7f) != 0x6f:
        return None
    imm = (((insn >> 31) & 1) << 20) | (((insn >> 12) & 0xff) << 12) | (((insn >> 20) & 1) << 11) | (((insn >> 21) & 0x3ff) << 1)
    return (pc + sx(imm, 21)) & 0xffffffff


def main():
    print('='*116)
    print('MILESTONE 3D - RTL JAL / JALR CALL-RETURN FETCH ANALYSIS')
    print('='*116)
    for name in CASES:
        fpath = os.path.join(RESULTS, 'fetch_' + name + '.csv')
        rpath = os.path.join(RESULTS, 'rtl_' + name + '.csv')
        if not os.path.exists(fpath) or not os.path.exists(rpath):
            print('\n{}: missing VCS fetch/retirement result'.format(name))
            continue
        fr = rows(fpath)
        rr = rows(rpath)
        retired_seq = [int(r['pc'],0) for r in rr]
        retired_set = set(retired_seq)
        print('\n{}\n{}'.format(name, '-'*len(name)))
        print('retired instructions : {}'.format(len(rr)))
        print('I$ accesses          : {}'.format(len(fr)))
        print('I$ hits              : {}'.format(sum(int(r['hit']) for r in fr)))
        print('I$ misses            : {}'.format(sum(int(r['miss']) for r in fr)))
        print('retired PCs          : ' + ', '.join('0x{:08x}'.format(x) for x in retired_seq))
        for i, r in enumerate(rr):
            pc = int(r['pc'],0)
            insn = int(r['insn'],0)
            opcode = insn & 0x7f
            if opcode not in (0x6f, 0x67):
                continue
            rd = (insn >> 7) & 0x1f
            next_pc = int(rr[i+1]['pc'],0) if i+1 < len(rr) else None
            if opcode == 0x6f:
                tgt = jal_target(pc, insn)
                print('JAL  @0x{:08x} rd=x{} target=0x{:08x} next_retired={}'.format(
                    pc, rd, tgt, '0x{:08x}'.format(next_pc) if next_pc is not None else 'none'))
            else:
                rs1 = (insn >> 15) & 0x1f
                imm = sx((insn >> 20) & 0xfff, 12)
                print('JALR @0x{:08x} rd=x{} rs1=x{} imm={} observed_target={}'.format(
                    pc, rd, rs1, imm, '0x{:08x}'.format(next_pc) if next_pc is not None else 'none'))

        print('\n  #  cycle       PC        hit/miss   retired-ever')
        print('  -- -----   ----------     --------   ------------')
        counts = {}
        for i,r in enumerate(fr,1):
            pc = int(r['pc'],0)
            counts[pc] = counts.get(pc,0)+1
            hm = 'HIT' if int(r['hit']) else 'MISS'
            print('{:4d} {:5d}   0x{:08x}     {:>4}       {}'.format(i,int(r['cycle']),pc,hm,'yes' if pc in retired_set else 'NO'))
        nonret = [int(r['pc'],0) for r in fr if int(r['pc'],0) not in retired_set]
        if nonret:
            uniq=[]
            for pc in nonret:
                if pc not in uniq:
                    uniq.append(pc)
            print('non-retired fetched PCs: ' + ', '.join('0x{:08x}'.format(x) for x in uniq))
        replay = [(pc,n) for pc,n in counts.items() if n > 1]
        if replay:
            print('re-fetched PCs         : ' + ', '.join('0x{:08x} x{}'.format(pc,n) for pc,n in sorted(replay)))
    print('\nUse the exact fetch order above to calibrate jump redirect latency and target-stream restart; do not infer it from aggregate cycles alone.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
