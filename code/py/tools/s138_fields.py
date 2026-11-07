#!/usr/bin/env python3
"""s138_fields: decode a dwRoomMessage (de)serializer into op list.
usage: s138_fields.py <VA>...
"""
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

WRITE_BITS, WRITE_DATA = 0x00B77B10, 0x00B777C0
READ_BITS, READ_DATA = 0x00B774E0, 0x00B772E0
READ_BLOB = 0x004F3EB0
KNOWN = {WRITE_BITS: 'B', WRITE_DATA: 'D', READ_BITS: 'R',
         READ_DATA: 'r', READ_BLOB: 'rb'}


def decode(va, max_insns=200):
    code = d[va - VA:va - VA + 0x600]
    insns = list(md.disasm(code, va))[:max_insns]
    ops = []
    pushes = []
    lastreg = None
    for ins in insns:
        m, o = ins.mnemonic, ins.op_str
        if m == 'push':
            if o.startswith('0x'):
                pushes.append(int(o, 16))
            elif o.lstrip('-').isdigit():
                pushes.append(int(o))
            else:
                pushes.append(None)
            pushes = pushes[-4:]
        elif m == 'mov' and o.startswith('dword ptr [esp'):
            v = o.rsplit(',', 1)[-1].strip()
            pushes.append(int(v, 16) if v.startswith('0x')
                          else (int(v) if v.lstrip('-').isdigit() else None))
            pushes = pushes[-4:]
        elif m == 'mov' and o.startswith('lea eax, [ebp'):
            # capture source operand hint
            lastreg = o
        elif m == 'call':
            tgt = int(o, 16) if o.startswith('0x') else None
            kind = KNOWN.get(tgt)
            if kind:
                vals = [v for v in pushes if v is not None]
                ops.append((kind, vals[0] if vals else None, vals))
            pushes = []
        elif m.startswith('j') or m == 'ret':
            pushes = []
        if m == 'ret':
            break
    return ops


for a in sys.argv[1:]:
    print("=" * 70)
    print("function", a)
    for kind, v, vals in decode(int(a, 0)):
        print("   %-3s %s   pushes=%s" % (kind, ('0x%X' % v) if v is not None else '?',
                                          [hex(x) for x in vals]))
