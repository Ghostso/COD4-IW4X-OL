#!/usr/bin/env python3
"""s138_callers.py <VA>... : E8 rel32 callers + FF15 abs-indirect callers.
Usage: python -I tools/s138_callers.py 0xB7A400 0xB7A4A0
"""
import struct
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, ml=100):
    o = va - VA
    if not (0 <= o < N - 1):
        return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2:
        return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


def entry_of(f):
    j = f
    while j > 1:
        if d[j - 1] == 0xCC and d[j - 2] == 0xCC:
            return VA + j
        j -= 1
    return None


def callers(t):
    out = []
    i = 0
    while True:
        i = d.find(b"\xe8", i)
        if i < 0:
            break
        if i + 5 <= N:
            rel = struct.unpack_from("<i", d, i + 1)[0]
            if VA + i + 5 + rel == t:
                out.append(VA + i)
        i += 1
    # absolute indirect: ff 15 <abs>
    i = 0
    while True:
        i = d.find(b"\xff\x15", i)
        if i < 0:
            break
        if i + 6 <= N:
            a = struct.unpack_from("<I", d, i + 2)[0]
            if a == t:
                out.append(VA + i)
        i += 1
    # mov reg,imm32 + call reg (call eax/ecx/edx/esi/edi/ebx = ff d0/d1/d2/d6/d7/d3)
    for m in re.finditer(b"\xb8([\x00-\xff]{4})", d):
        imm = struct.unpack("<I", m.group(1))[0]
        if imm != t:
            continue
        # scan next 24 bytes for ff d0
        seg = d[m.end():m.end() + 24]
        for k in range(0, max(0, len(seg) - 1)):
            if seg[k] == 0xFF and seg[k + 1] in (0xD0, 0xD1, 0xD2, 0xD3, 0xD6, 0xD7):
                out.append(VA + m.start() + k)
                break
    return out


for arg in sys.argv[1:]:
    t = int(arg, 0)
    cs = callers(t)
    print("\n=== 0x%08X: %d callers ===" % (t, len(cs)))
    for c in cs:
        e = entry_of(c - VA)
        print("  call@0x%08X  in func 0x%08X" % (c, e or 0))
