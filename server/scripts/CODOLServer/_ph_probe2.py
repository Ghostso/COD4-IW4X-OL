#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 2: SetKey jump table, call-site prologue, context lifecycle."""

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

    def va_to_off(va):
        rva = va - ib
        for nm, rv, raw, sz in secs:
            if rv <= rva < rv + sz:
                return raw + (rva - rv), nm
        return None, None

    md = Cs(CS_ARCH_X86, CS_MODE_32)

    def dis(va, n, label):
        off, nm = va_to_off(va)
        print('')
        print('=== %s VA=%08X file_off=0x%X ===' % (label, va, off or 0))
        if off is None:
            return
        for ins in md.disasm(d[off:off + n], va):
            print('  %08X  %-10s %s' % (ins.address, ins.mnemonic,
                                         ins.op_str))

    print('=== SetKey jump table @ 0x10063E78 (4 entries) ===')
    off, nm = va_to_off(0x10063E78)
    for i in range(4):
        v = struct.unpack_from('<I', d, off + i * 4)[0]
        print('  mode=%d -> 0x%08X' % (i, v))

    print('')
    print('=== stack-frame window of SetKey (prologue only) ===')
    dis(0x10063DF0, 0x30, 'SetKey prologue')
    print('')
    for tgt in (0x10063E0D, 0x10063E33, 0x10063E8B, 0x10063E94):
        dis(tgt, 0x30, 'SetKey case @%08X' % tgt)

    # find the real function start of the call site
    print('')
    print('=== call-site function: search back for prologue from 0x10064DB0 ===')
    off, nm = va_to_off(0x10064DB0)
    s = off
    while s > 0 and off - s < 0x2000:
        if d[s:s + 3] == b'\x55\x8b\xec':
            break
        if d[s] == 0x81 and d[s + 1] == 0xec:      # sub esp, imm32
            break
        s -= 1
    nm2, rva2 = None, None
    rva2 = (ib - ib) + (0x10064DB0 - ib) - (off - s)
    print('  candidate prologue file_off=0x%X VA=0x%08X'
          % (s, ib + (s - secs[0][2]) if secs[0][2] <= s else 0))
    dis(ib + (s - 0x1000) + 0x1000 if False else 0x10000000 + (s - 0x1000),
        0x90, 'call-site prologue window')

    print('')
    print('=== full call-site frame setup (0x10064C00..0x10064DB8) ===')
    o1, _ = va_to_off(0x10064900)
    for ins in md.disasm(d[o1:va_to_off(0x10064DB8)[0]], 0x10064900):
        if ins.mnemonic in ('sub', 'add') and 'esp' in ins.op_str:
            print('  %08X  %-10s %s' % (ins.address, ins.mnemonic,
                                         ins.op_str))
        elif ins.mnemonic == 'lea' and 'esp' in ins.op_str:
            print('  %08X  %-10s %s' % (ins.address, ins.mnemonic,
                                         ins.op_str))
        elif ins.mnemonic == 'call':
            print('  %08X  %-10s %s' % (ins.address, ins.mnemonic,
                                         ins.op_str))


if __name__ == '__main__':
    main()
