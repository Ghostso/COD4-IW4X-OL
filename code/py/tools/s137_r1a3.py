#!/usr/bin/env python3
"""137 R1a: locate playlist-table code and [this+0x105fc] accesses."""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def find_all(pat):
    out, pos = [], 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        out.append(i)
    return out


def ctx(i, n=8):
    return d[max(0, i - n):i + n].hex(" ")


def cstr(va, maxlen=48):
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


def scan_disp(name, disp):
    pat = struct.pack("<I", disp)
    hits = [VA + i for i in find_all(pat)]
    print("== disp 0x%X (%s): %d ==" % (disp, name, len(hits)))
    for h in hits[:60]:
        print("   0x%08X  %s" % (h, ctx(h - VA, 8)))


def scan_imm(name, imm):
    pat = struct.pack("<I", imm)
    hits = [VA + i for i in find_all(pat)]
    print("== imm32 0x%X (%s): %d ==" % (imm, name, len(hits)))
    for h in hits[:60]:
        print("   0x%08X  %s" % (h, ctx(h - VA, 8)))


scan_disp("+0x105fc", 0x105FC)
scan_disp("+0x105d8", 0x105D8)
scan_disp("+0x105f8", 0x105F8)
scan_imm("0x3e24", 0x3E24)
scan_disp("table base 0x7b29730", 0x7B29730)
scan_disp("table 0x7b29778", 0x7B29778)
scan_disp("0x8004499", 0x8004499)
