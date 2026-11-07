#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VM ISA probe 10: find AES key-expansion via OpenSSL rcon xrefs."""

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

    # OpenSSL rcon arrays discovered at .rdata:0x782D03 and .rdata:0x983F...
    # Try both the table start and the +3 byte position used by byte loads.
    targets = [0x782CF0, 0x782D00, 0x782D03, 0x782D04,
               0x983F00, 0x983F10, 0x983F13, 0x983F14,
               0x9CF500, 0x9CF570]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for rva in targets:
        linked = ib + rva
        pat = struct.pack('<I', linked)
        xr = []
        pos = 0
        while len(xr) < 12:
            j = d.find(pat, pos)
            if j < 0:
                break
            xr.append(j)
            pos = j + 1
        print('rva %08X linked %08X xrefs=%s'
              % (rva, linked, [owner(x)[:2] for x in xr]))

    print('')
    print('=== disasm around first .text xref to rcon ==')
    for rva in (0x782D03, 0x782D04, 0x983F13, 0x983F14):
        linked = ib + rva
        pat = struct.pack('<I', linked)
        j = d.find(pat)
        if j < 0:
            continue
        nm, orva, ova = owner(j)
        print('--- xref file_off=0x%X %s:%08X ---' % (j, nm, orva))
        start = max(0, j - 160)
        start_va = owner(start)[2] or 0
        for ins in md.disasm(d[start:start + 400], start_va):
            print('  %08X  %-9s %s' % (ins.address, ins.mnemonic,
                                       ins.op_str))

    print('')
    print('=== candidate AES key-expansion function prologues ===')
    # For each xref, walk back to nearest 55 8B EC within 4KB.
    seen = set()
    for rva in (0x782D03, 0x782D04, 0x983F13, 0x983F14):
        linked = ib + rva
        pat = struct.pack('<I', linked)
        j = d.find(pat)
        if j < 0:
            continue
        s = j
        while s > 0 and j - s < 0x4000:
            if d[s:s + 3] == b'\x55\x8b\xec':
                break
            s -= 1
        nm, srva, sva = owner(s)
        if srva in seen:
            continue
        seen.add(srva)
        print('  xref %s:%08X -> prologue .text:%08X'
              % (nm, owner(j)[1], srva))
        # print first 40 instructions
        for n, ins in enumerate(md.disasm(d[s:s + 400], sva)):
            if n >= 40:
                break
            print('    %08X  %-9s %s' % (ins.address, ins.mnemonic,
                                          ins.op_str))


if __name__ == '__main__':
    main()
