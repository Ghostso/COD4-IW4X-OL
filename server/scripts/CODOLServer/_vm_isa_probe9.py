#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM ISA probe 9: locate AES key-setup function(s) in Base.dll."""

import os
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLL = os.path.join(ROOT, 'COD OL', 'codoMP_client_shipRetailBase.dll')


def main():
    d = open(DLL, 'rb').read()
    pe = pefile.PE(data=d, fast_load=True)
    ib = pe.OPTIONAL_HEADER.ImageBase
    secs = [(s.Name.rstrip(b'\x00').decode('latin1'),
             s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData)
            for s in pe.sections]

    def owner(off):
        for nm, rv, raw, sz in secs:
            if raw <= off < raw + sz:
                return nm, rv + (off - raw), ib + rv + (off - raw)
        return None, None, None

    md = Cs(CS_ARCH_X86, CS_MODE_32)

    def disasm_window(off, before=128, length=512):
        nm, rva, va = owner(off)
        print('--- %s file_off=0x%X rva=%08X va=%08X ---'
              % (nm, off, rva, va))
        start = max(0, off - before)
        start_va = owner(start)[2] or 0
        for ins in md.disasm(d[start:start + length], start_va):
            mark = ' <==' if start + (ins.address - start_va) == off else ''
            print('  %08X  %-9s %-30s%s'
                  % (ins.address, ins.mnemonic, ins.op_str, mark))

    print('=== string xrefs -> AES key setup / ECB implementation ===')
    targets = [b'aes key setup failed', b'AES_INIT_KEY',
               b'aes-128-ecb', b'aes-256-ecb', b'bad decrypt']
    for s in targets:
        i = d.find(s)
        if i < 0:
            continue
        nm, rva, va = owner(i)
        pat = struct.pack('<I', va)
        xr = []
        pos = 0
        while len(xr) < 12:
            j = d.find(pat, pos)
            if j < 0:
                break
            xr.append(j)
            pos = j + 1
        print('%r -> %s:%08X (va=%08X) xrefs=%s'
              % (s, nm, rva, va, [owner(x)[:2] for x in xr]))
        for j in xr[:2]:
            disasm_window(j)

    print('')
    print('=== .text xrefs to AES inverse S-box @ .rdata:0x782C00 ===')
    linked = ib + 0x782C00
    pat = struct.pack('<I', linked)
    xr = []
    pos = 0
    while len(xr) < 8:
        j = d.find(pat, pos)
        if j < 0:
            break
        xr.append(j)
        pos = j + 1
    print('linked=%08X xrefs=%s' % (linked, [owner(x)[:2] for x in xr]))
    for j in xr[:3]:
        disasm_window(j, before=192, length=512)

    print('')
    print('=== best function-start guesses before each xref ===')
    for j in xr[:6]:
        start = j
        while start > 0 and d[start:start + 3] != b'\x55\x8b\xec':
            start -= 1
            if j - start > 0x2000:
                break
        nm, rva, va = owner(start)
        print('  xref %08X -> prologue %s:%08X'
              % (owner(j)[1], nm, rva))


if __name__ == '__main__':
    main()
