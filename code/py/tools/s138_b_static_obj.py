#!/usr/bin/env python3
"""s138_b_static_obj: resolve the static object at a given VA's vtable and slots.
Usage: python -I tools/s138_b_static_obj.py <objVA> [slot1 slot2 ...]
"""
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def u32(va):
    o = va - VA
    if 0 <= o <= N - 4:
        return struct.unpack_from("<I", d, o)[0]
    return None


def cstr(va, ml=120):
    o = va - VA
    if not (0 <= o < N - 1):
        return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2:
        return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


def rtti_name(vt):
    """MSVC COL at [vt-4]: pTypeDescriptor@col+0x0C; name at td+8."""
    col = u32(vt - 4)
    if not col:
        return None
    td = u32(col + 0x0C)
    if not td:
        return None
    return cstr(td + 8) or ("<raw td 0x%08X>" % td)


def dis(va, n=0x50):
    code = d[va - VA:va - VA + n]
    for ins in md.disasm(code, va):
        print("    0x%08X  %-16s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if ins.mnemonic.startswith("ret"):
            break


obj = int(sys.argv[1], 0)
slots = [int(x, 0) for x in sys.argv[2:]] or [0x28]
print("object 0x%08X:" % obj)
for off in range(0, min(0x30, 0x30), 4):
    v = u32(obj + off)
    print("  +0x%02X = 0x%08X" % (off, v or 0))
vt = u32(obj)
print("\nvtable = 0x%08X" % (vt or 0))
print("COL     = 0x%08X" % (u32(vt - 4) or 0))
print("RTTI    = %s" % (rtti_name(vt) or "?"))
print("\nfirst 16 vtable entries:")
for k in range(16):
    print("  vt+0x%02X = 0x%08X" % (4 * k, u32(vt + 4 * k) or 0))
for s in slots:
    f = u32(vt + s)
    print("\nslot +0x%02X -> 0x%08X" % (s, f or 0))
    if f and 0 <= f - VA < N:
        dis(f, 0x80)
