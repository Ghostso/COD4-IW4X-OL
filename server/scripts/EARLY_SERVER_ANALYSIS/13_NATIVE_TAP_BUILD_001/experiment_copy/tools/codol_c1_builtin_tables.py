#!/usr/bin/env python3
"""Dump C1.exe (CoDOL 1.1.1.13) GSC builtin tables with string hints.

Read-only static analysis. C1 keeps its server-side script builtins in
12-byte records {const char *name, void (*fn)(), int developer}, but every
name pointer is the pooled empty string 0xc2fead: the names were stripped.
This finds the record runs by that pointer, walks each run while the records
stay well formed, and prints every entry's handler plus the first rdata
strings the handler pushes directly (error/usage text), which is usually
enough to name it ("illegal call to GetBaseFromCustomWeapon(...)").

Ten tables, 1356 records, in 1.1.1.13 (start: count, contents):
  0xc30da8: 122 actor methods        0xc32828:  94 vehicle methods
  0xc39d40:  13 sentient methods     0xc39de0:   7 threat-bias functions
  0xc3a2a0: 229 entity methods       0xc3b430: 262 player methods
  0xcd24f0:  23 hud element methods  0xcd2638: 241 functions (T5/SP/CoDOL)
  0xcd3190: 164 entity methods (2)   0xcd3978: 201 functions (IW4 order)

Order is informative: 0xcd3978 keeps IW4's function order, so an entry whose
IW4 neighbours are known can be named by position (entry 148 is
weaponhasthermalscope, between isweapondetonationtimed and the vehicle-node
functions). Handlers without direct strings print no hint.

    python tools/codol_c1_builtin_tables.py > c1_builtins.tsv

SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_argv, sys.argv = sys.argv, sys.argv[:1]   # codol_c1_disasm parses argv on import
from codol_c1_disasm import PE, md          # noqa: E402
sys.argv = _argv

EXE = r'D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/C1.exe'
EMPTY_NAME = 0xc2fead
RDATA = (0xb42000, 0xc9a000)
TEXT = (0x401000, 0xb42000)


def main():
    pe = PE(sys.argv[1] if len(sys.argv) > 1 else EXE)

    def u32(va):
        b = pe.read(va, 4)
        return struct.unpack('<I', b)[0] if b and len(b) == 4 else None

    def cstr(va):
        b = pe.read(va, 96)
        if not b:
            return None
        s = b.split(b'\0')[0]
        if len(s) < 3:
            return None
        try:
            t = s.decode('ascii')
        except UnicodeDecodeError:
            return None
        return t if all(32 <= ord(c) < 127 or c in '\n\t' for c in t) else None

    def record(va):
        n, f, dev = u32(va), u32(va + 4), u32(va + 8)
        if n is None or f is None or dev not in (0, 1):
            return None
        if not (RDATA[0] <= n < RDATA[1] and TEXT[0] <= f < TEXT[1]):
            return None
        return n, f, dev

    def hints(fn, limit=400):
        out = []
        for n, ins in enumerate(md().disasm(pe.read(fn, 3000), fn)):
            for m in re.finditer(r'0x([0-9a-f]{6,8})', ins.op_str):
                v = int(m.group(1), 16)
                if RDATA[0] <= v < RDATA[1]:
                    s = cstr(v)
                    if s and s not in out:
                        out.append(s)
            if ins.mnemonic == 'ret' or n > limit:
                break
        return out

    pattern = struct.pack('<I', EMPTY_NAME)
    starts = set()
    for name, sva, vsz, ra, rsz in pe.sections:
        blob = pe.data[ra:ra + rsz]
        i = blob.find(pattern)
        while i >= 0:
            va = sva + i
            if record(va) and record(va + 12):
                while record(va - 12):
                    va -= 12
                starts.add(va)
            i = blob.find(pattern, i + 1)
    for start in sorted(starts):
        va, index = start, 0
        print('# table 0x%x' % start)
        while record(va):
            n, f, dev = record(va)
            label = '' if n == EMPTY_NAME else (cstr(n) or '')
            text = ' | '.join(s.replace('\n', '\\n')[:80] for s in hints(f)[:4])
            print('%d\t0x%x\t0x%x\t%d\t%s\t%s' % (index, va, f, dev, label, text))
            va += 12
            index += 1


if __name__ == '__main__':
    main()
