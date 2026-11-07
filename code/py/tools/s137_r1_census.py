#!/usr/bin/env python3
"""137 vol R1: playlist 37 定名 - string/reference census."""
import struct
import sys

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def cstr(va, maxlen=120):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        e = f + maxlen
    try:
        return d[f:e].decode("latin1")
    except Exception:
        return None


def find_all(pat):
    out = []
    pos = 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        out.append(i)
    return out


def refs_to(va, width=4):
    pat = struct.pack("<I", va)
    return [VA + i for i in find_all(pat)]


def dump_hex(va, ln):
    f = va - VA
    print("--- bytes @0x%08X (%d) ---" % (va, ln))
    for r in range(0, ln, 16):
        chunk = d[f + r:f + r + 16]
        print("  %08X  %s  %s" % (va + r, chunk.hex(" "),
                                  "".join(chr(c) if 32 <= c < 127 else "."
                                            for c in chunk)))


print("== string pool near 0xDC259B ==")
dump_hex(0xDC2570, 0xA0)
print()
print("== RTTI region near 0xE6C5BF ==")
dump_hex(0xE6C590, 0x80)
print()
print("== name table region near 0x038322CC ==")
dump_hex(0x03832290, 0x90)

for s in ("GetPlayListIdForNum", "GetPlayListNumForId",
          "PlayListGetType", "AS_PlayListGetType"):
    print()
    print("== refs to string text '%s' ==" % s)
    hits = find_all(s.encode())
    for i in hits:
        print("   str @0x%08X" % (VA + i))
