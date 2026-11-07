#!/usr/bin/env python3
"""s138_srpc_table: dump the (svc,task)->callback table at 0xE376C08, stride 0x25D0.
Fields used by 0x7E7C90: [esi-0x25B8] byte flag, [esi-0x25B7] byte flag,
[esi-0x25A8] u32 svc, [esi-0x25A4] u32 task, [esi] fnptr.
Usage: python -I tools/s138_srpc_table.py [baseVA]
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

BASE = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0xE376C08
STRIDE = 0x25D0
END = 0xE37B7A8


def u32(va):
    o = va - VA
    if 0 <= o <= N - 4:
        return struct.unpack_from("<I", d, o)[0]
    return None


def u8(va):
    o = va - VA
    return d[o] if 0 <= o < N else None


print("base 0x%08X stride 0x%X" % (BASE, STRIDE))
n = 0
for a in range(BASE, END, STRIDE):
    svc = u32(a - 0x25A8)
    task = u32(a - 0x25A4)
    fn = u32(a)
    f1 = u8(a - 0x25B8)
    f2 = u8(a - 0x25B7)
    print("[%2d] entry 0x%08X  svc=%6s task=%6s  f=(%s,%s) fn=0x%08X"
          % (n, a, svc, task, f1, f2, fn or 0))
    n += 1
print("total", n)
