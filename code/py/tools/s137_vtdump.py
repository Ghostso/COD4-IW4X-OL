#!/usr/bin/env python3
"""137: dump vtable region + COL for a set of addresses."""
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


def rd(va):
    f = va - VA
    if 0 <= f < N - 4:
        return struct.unpack_from("<I", d, f)[0]
    return None


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    try:
        return d[f:e].decode("latin1")
    except Exception:
        return None


def dump_hex(va, ln):
    f = va - VA
    for r in range(0, ln, 16):
        c = d[f + r:f + r + 16]
        vals = " ".join("%08x" % struct.unpack_from("<I", (c + b"\0\0\0\0")[:4])[0]
                        if False else "" for _ in [0]) if False else ""
        print("  %08X  %s  %s" % (va + r, c.hex(" "),
                                  "".join(chr(x) if 32 <= x < 127 else "."
                                          for x in c)))


def dump_ptrs(va, n, label=""):
    print("--- ptr dump %s @0x%08X ---" % (label, va))
    for k in range(n):
        v = rd(va + 4 * k)
        s = ""
        if v and VA <= v < VA + N:
            s = cstr(v, 40) or ""
        print("  +0x%03X  %08X  %r" % (4 * k, v or 0, s))


def dis(va, ln, label=""):
    print("=== disasm %s @0x%08X ===" % (label, va))
    f = va - VA
    for ins in md.disasm(d[f:f + ln], va):
        line = "  0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(),
                                          ins.mnemonic, ins.op_str)
        for tok in re.findall(r"0x[0-9a-f]+", ins.op_str):
            v = int(tok, 16)
            if VA <= v < VA + N and v % 4 == 0:
                s = cstr(v, 60)
                if s:
                    line += "   ; '%s'" % s
                    break
        print(line)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        va = int(a, 0)
        print("###### around 0x%08X" % va)
        dump_hex(va - 0x10, 0x40)
        dump_ptrs(va - 0x10, 16, "")
        print()
