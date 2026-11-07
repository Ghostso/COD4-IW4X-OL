#!/usr/bin/env python3
"""s137: 找 call <VA> 的调用点 + 打印调用点前 0x40 字节反汇编."""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, maxlen=70):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 or c in (9, 10) for c in s) else None


def callsites(tgt):
    res = []
    for i in range(N - 5):
        if d[i] == 0xE8:
            rel = struct.unpack_from("<i", d, i + 1)[0]
            if (VA + i + 5 + rel) & 0xFFFFFFFF == tgt & 0xFFFFFFFF:
                res.append(i)
    return res


for a in sys.argv[1:]:
    tgt = int(a, 0)
    cs = callsites(tgt)
    print("=== call 0x%08X : %d 处 ===" % (tgt, len(cs)))
    for i in cs:
        print("  call@VA 0x%08X" % (VA + i))
