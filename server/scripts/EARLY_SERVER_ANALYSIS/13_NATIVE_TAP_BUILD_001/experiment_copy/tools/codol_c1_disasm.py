#!/usr/bin/env python3
"""Minimal C1.exe (CoDOL 1.1.1.13) static disassembly helper.

Read-only. Loads the PE by section, maps virtual addresses, and offers:
  --func ADDR [--max N]      linear disassembly from ADDR until ret/int3 run
  --range A B                linear disassembly of an address range
  --xref ADDR                every instruction whose operand text contains the
                             hex address (immediate or [disp32]); a poor man's
                             xref that is enough to find constant users
  --float ADDR [N]           print N floats at ADDR
  --find-bytes HEX           byte-pattern search, prints virtual addresses

Used by docs/CODOL_UNEVEN_GROUND_FIX_SWEEP.md to read the client's
PM_GroundTrace / CM_Trace shape.  SPDX-License-Identifier: AGPL-3.0-or-later
"""
import argparse, struct, sys, re
import capstone

class PE:
    def __init__(self, path):
        d = open(path, 'rb').read()
        self.data = d
        pe = struct.unpack_from('<I', d, 0x3c)[0]
        assert d[pe:pe+4] == b'PE\0\0'
        nsec = struct.unpack_from('<H', d, pe+6)[0]
        optsz = struct.unpack_from('<H', d, pe+20)[0]
        self.base = struct.unpack_from('<I', d, pe+24+28)[0]
        self.sections = []
        off = pe+24+optsz
        for i in range(nsec):
            name = d[off:off+8].rstrip(b'\0').decode('latin1')
            vsz, va, rsz, ra = struct.unpack_from('<IIII', d, off+8)
            self.sections.append((name, va+self.base, vsz, ra, rsz))
            off += 40
    def off(self, va):
        for name, sva, vsz, ra, rsz in self.sections:
            if sva <= va < sva+max(vsz, rsz):
                o = ra + (va - sva)
                if o < len(self.data):
                    return o
        return None
    def read(self, va, n):
        o = self.off(va)
        return None if o is None else self.data[o:o+n]

def md():
    m = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    m.detail = False
    return m

def disas(pe, va, n=4096, stop_on_ret=True):
    buf = pe.read(va, n)
    out = []
    depth = 0
    for i in md().disasm(buf, va):
        out.append('%08x  %-24s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
        if stop_on_ret and i.mnemonic in ('ret', 'retn') :
            depth += 1
            if depth >= 1:
                break
        if i.mnemonic == 'int3':
            break
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', default=r'D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/C1.exe')
    ap.add_argument('--func'); ap.add_argument('--range', nargs=2)
    ap.add_argument('--xref'); ap.add_argument('--float', nargs='+')
    ap.add_argument('--find-bytes'); ap.add_argument('--max', type=int, default=4096)
    ap.add_argument('--no-stop', action='store_true')
    a = ap.parse_args()
    pe = PE(a.exe)
    if a.func:
        va = int(a.func, 16)
        print('\n'.join(disas(pe, va, a.max, not a.no_stop)))
    if a.range:
        lo, hi = int(a.range[0], 16), int(a.range[1], 16)
        print('\n'.join(disas(pe, lo, hi-lo, False)))
    if a.float:
        va = int(a.float[0], 16); n = int(a.float[1]) if len(a.float) > 1 else 1
        b = pe.read(va, 4*n)
        print(' '.join('%.9g' % f for f in struct.unpack('<%df' % n, b)))
    if a.find_bytes:
        pat = bytes.fromhex(a.find_bytes)
        for name, sva, vsz, ra, rsz in pe.sections:
            blob = pe.data[ra:ra+rsz]
            i = blob.find(pat)
            while i >= 0:
                print('%08x (%s)' % (sva+i, name)); i = blob.find(pat, i+1)
    if a.xref:
        target = int(a.xref, 16)
        needle = '%x' % target
        for name, sva, vsz, ra, rsz in pe.sections:
            if name not in ('.text', 'text', '.code'): continue
            blob = pe.data[ra:ra+rsz]
            for i in md().disasm(blob, sva):
                if needle in i.op_str.lower():
                    print('%08x  %s %s' % (i.address, i.mnemonic, i.op_str))
main()
