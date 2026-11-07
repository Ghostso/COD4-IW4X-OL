#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
runtime_code_analysis.py -- disassemble the dynamic CODOL runtime code buffer.

Reads runtime_target_range.json + runtime_code.bin + sentinel_table.bin from a
dump directory, maps sentinel slots to function entry offsets, performs
recursive-ish linear disassembly from those entries, and reports:
  * function entry map
  * call/jmp targets
  * absolute data/sentinel references
  * FF15 slot references
  * the most common external targets

Usage:
    python runtime_code_analysis.py --dir <dump_dir>
"""

import argparse
import collections
import csv
import json
import os
import struct
import sys

import capstone


def load(path, base=0):
    with open(path, 'rb') as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    args = ap.parse_args()

    meta = json.load(open(os.path.join(args.dir, 'runtime_target_range.json'),
                          encoding='utf-8'))
    base = int(meta['base'])
    code = load(os.path.join(args.dir, 'runtime_code.bin'))
    sentinel = load(os.path.join(args.dir, 'sentinel_table.bin'))

    entries = {}
    for i in range(0, len(sentinel), 4):
        v = struct.unpack_from('<I', sentinel, i)[0]
        if base <= v < base + len(code):
            entries.setdefault(v, []).append(0x00CA8000 + i)

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    md.skipdata = True

    insn_rows = []
    direct_targets = collections.Counter()
    imm_targets = collections.Counter()
    ff15_slots = collections.Counter()
    entry_rows = []

    for entry in sorted(entries):
        entry_rows.append((entry, entry - base, len(entries[entry]),
                           entries[entry][0]))
        end = min(len(code), entry - base + 256)
        for ins in md.disasm(code[entry - base:end], entry):
            if ins.address > entry + 512:
                break
            op = ins.op_str
            insn_rows.append((entry, ins.address, ins.mnemonic, op,
                              ins.bytes.hex(' ')))
            if ins.id == 0:
                continue
            if ins.mnemonic in ('call', 'jmp') and ins.operands:
                opnd = ins.operands[0]
                if opnd.type == capstone.x86.X86_OP_IMM:
                    direct_targets[opnd.imm] += 1
                elif opnd.type == capstone.x86.X86_OP_MEM and opnd.mem.disp:
                    ff15_slots[opnd.mem.disp] += 1
            # absolute immediate operands (push/mov/lea/etc)
            try:
                for opnd in ins.operands:
                    if opnd.type == capstone.x86.X86_OP_IMM:
                        v = opnd.imm & 0xFFFFFFFF
                        if 0x00400000 <= v <= 0x14000000:
                            imm_targets[v] += 1
            except capstone.CsError:
                pass
            if ins.mnemonic in ('ret', 'retf') or (
                    ins.mnemonic == 'int3' and ins.address > entry + 4):
                break

    out_md = os.path.join(args.dir, 'runtime_code_analysis.md')
    out_csv = os.path.join(args.dir, 'runtime_code_analysis.csv')
    with open(out_csv, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['entry_va', 'insn_va', 'mnemonic', 'operands', 'bytes'])
        w.writerows(insn_rows)

    with open(out_md, 'w', encoding='utf-8') as fh:
        fh.write('# CODOL dynamic runtime code analysis\n\n')
        fh.write('base=0x%08X size=0x%X entries=%d insns=%d\n\n'
                 % (base, len(code), len(entries), len(insn_rows)))
        fh.write('## Sentinel entries\n\n')
        for va, off, n, slot in entry_rows[:500]:
            fh.write('- entry=0x%08X off=0x%04X slots=%d first=0x%08X\n'
                     % (va, off, n, slot))
        fh.write('\n## Direct call/jmp targets\n\n')
        for va, n in direct_targets.most_common(200):
            fh.write('- 0x%08X x%d\n' % (va, n))
        fh.write('\n## Absolute immediates in image/runtime range\n\n')
        for va, n in imm_targets.most_common(300):
            fh.write('- 0x%08X x%d\n' % (va, n))
        fh.write('\n## FF15-style slot references\n\n')
        for va, n in ff15_slots.most_common(200):
            fh.write('- 0x%08X x%d\n' % (va, n))
        fh.write('\n## First 250 instructions\n\n```text\n')
        for row in insn_rows[:250]:
            fh.write('%08X  %-10s %s\n' % (row[1], row[2], row[3]))
        fh.write('```\n')

    print('wrote', out_md)
    print('entries=%d insns=%d direct=%d imm=%d ff15=%d'
          % (len(entries), len(insn_rows), len(direct_targets),
             len(imm_targets), len(ff15_slots)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
