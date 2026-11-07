#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 3: exact call-site sequence, heap alloc size, context layout."""

import os
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL = os.path.join(ROOT, 'COD OL', 'Cross', 'ProtocalHandler.dll')


def main():
    d = open(DLL, 'rb').read()
    pe = pefile.PE(data=d, fast_load=True)
    ib = pe.OPTIONAL_HEADER.ImageBase
    secs = [(s.Name.rstrip(b'\x00').decode('latin1'),
             s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData)
            for s in pe.sections]

    def off(va):
        rva = va - ib
        for nm, rv, raw, sz in secs:
            if rv <= rva < rv + sz:
                return raw + (rva - rv)
        return None

    md = Cs(CS_ARCH_X86, CS_MODE_32)

    def dis(va, n, label):
        print('')
        print('=== %s VA=%08X ===' % (label, va))
        o = off(va)
        for ins in md.disasm(d[o:o + n], va):
            print('  %08X  %-10s %s' % (ins.address, ins.mnemonic,
                                         ins.op_str))

    dis(0x10064D70, 0x60, 'keygen + SetKey call site (exact)')

    print('')
    print('=== heap alloc sizes (push imm32 near ctor) ===')
    for size in (0x2b0, 0x2b4, 0x2b8, 0x2c0, 0x298, 0x110, 0x120, 0x2f0):
        pat = b'\x68' + struct.pack('<I', size)
        hits = []
        s = 0
        while len(hits) < 8:
            j = d.find(pat, s)
            if j < 0:
                break
            hits.append(hex(j))
            s = j + 1
        if hits:
            print('  push 0x%X : %s' % (size, hits))

    dis(0x10062710, 0x60, 'ctor/init 0x10062710')

    print('')
    print('=== SetKey field writes ===')
    o = off(0x10063DF0)
    for ins in md.disasm(d[o:o + 0x90], 0x10063DF0):
        if ins.mnemonic in ('mov', 'add', 'lea', 'cmp') and (
                'ecx' in ins.op_str or 'edx' in ins.op_str):
            print('  %08X  %-8s %s' % (ins.address, ins.mnemonic,
                                        ins.op_str))

    print('')
    print('=== AES_set_encrypt_key field writes ===')
    o = off(0x10077E90)
    for ins in md.disasm(d[o:o + 0xC0], 0x10077E90):
        if 'ptr [edx' in ins.op_str or 'ptr [ecx' in ins.op_str:
            print('  %08X  %-8s %s' % (ins.address, ins.mnemonic,
                                        ins.op_str))

    print('')
    print('=== RNG globals ===')
    for va in (0x100fcf50, 0x100da098, 0x100da090):
        o = off(va)
        if o is None:
            print('  %08X unmapped' % va)
            continue
        b = d[o:o + 80]
        print('  %08X : %s' % (va, b[:70].hex()))
        print('         asc: %r' % b[:70])

    print('')
    print('=== AES T-table bases (first 4 dwords) ===')
    for va in (0x100da0b4, 0x100da4b4, 0x100db0b4, 0x100db4b4,
               0x100db8b4, 0x100dbcb4, 0x100dc1b4):
        o = off(va)
        if o is None:
            print('  %08X unmapped' % va)
            continue
        words = struct.unpack_from('<4I', d, o)
        print('  %08X : %s' % (va, ' '.join('%08X' % w for w in words)))

    print('')
    print('=== context offsets seen across the module ===')
    # find all [reg+0xNN] on ecx/esi that look like the ctx (0x4c, 0x50,
    # 0x84, 0x90, 0xf0, 0xf4)
    targets = (0x4c, 0x50, 0x84, 0x90, 0xf0, 0xf4)
    for t in targets:
        pat = b'\x50' + bytes([t]) if t < 0x100 else None
        cnt = d.count(bytes([t]))
        print('  offset 0x%02X : byte 0x%02X appears %d times'
              % (t, t, cnt))


if __name__ == '__main__':
    main()
