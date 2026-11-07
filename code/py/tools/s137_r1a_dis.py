#!/usr/bin/env python3
"""137 R1a: dump strings & disasm around the two playlist AS handlers."""
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dump_hex(va, ln):
    f = va - VA
    print("--- bytes @0x%08X ---" % va)
    for r in range(0, ln, 16):
        c = d[f + r:f + r + 16]
        print("  %08X  %s  %s" % (va + r, c.hex(" "),
                                  "".join(chr(x) if 32 <= x < 127 else "."
                                          for x in c)))


def cstr(va, maxlen=100):
    f = va - VA
    if not (0 <= f < N):
        return None
    s = f
    # backtrack to start of run
    while s > 0 and 32 <= d[s - 1] < 127:
        s -= 1
    e = d.find(b"\x00", s)
    if e < 0 or e - s > maxlen:
        return None
    return d[s:e].decode("latin1")


def dis(va, ln, label=""):
    print("=== disasm %s @0x%08X ===" % (label, va))
    f = va - VA
    for ins in md.disasm(d[f:f + ln], va):
        line = "  0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(),
                                          ins.mnemonic, ins.op_str)
        for tok in re.findall(r"0x[0-9a-f]+", ins.op_str):
            v = int(tok, 16)
            if VA <= v < VA + N and v % 4 == 0:
                s = cstr(v)
                if s:
                    line += "   ; '%s'" % s
                    break
        print(line)


print("### string regions")
dump_hex(0xDC0B40, 0x60)
print()
dump_hex(0xDD6050, 0x40)
print()
print("cstr(0xdc0b78) = %r" % cstr(0xDC0B78))
print("cstr(0xdd6070) = %r" % cstr(0xDD6070))
print()
dis(0x5D42C0, 0xE8, "AS_GetPlayListIdForNum")
print()
dis(0x5D09C0, 0x4A, "AS_GetPlayListNumForId")
print()
dis(0x761740, 0x60, "callee of NumForId")
print()
dis(0x761790, 0x60, "callee of 0x5D0A10")
print()
dis(0x5D39E0, 0xE8, "AS_SetRecommendedSetting (131)")
print()
dis(0x5D3790, 0xE8, "AS_TencentReportBadLanguage (131)")
print()
dis(0x5D07F0, 0x80, "AS_PlayListGetType candidate")
