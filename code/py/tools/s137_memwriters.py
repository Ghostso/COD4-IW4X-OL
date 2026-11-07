#!/usr/bin/env python3
"""137 R1b: locate writes/reads of member-record field offsets."""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

# member record offsets (from serializer 0x623880) + room offsets
OFFS = [0x00, 0x88, 0x8C, 0x90, 0x94, 0x96, 0x98, 0x99, 0xA0, 0xA8, 0xAC,
        0xB0, 0xB2, 0xB4, 0xB6, 0xB8, 0xBA, 0x1A0, 0x1A2, 0x1A4, 0x1A8,
        0x1AC, 0x1B0, 0x1B8, 0x1C0, 0x1C4, 0x1C8,
        0x105D8, 0x105FC, 0x105F8, 0xE368]

STORE1 = {0x88: "movb", 0x89: "movd", 0xC6: "movbi", 0xC7: "movdi"}
STORE2 = {0x0F: "sse?"}


def classify(i):
    """i = index of disp32 start. Look back for opcode."""
    b2 = d[i - 2] if i >= 2 else None
    b3 = d[i - 3] if i >= 3 else None
    b1 = d[i - 1] if i >= 1 else None
    # [op][modrm][disp32]
    if b2 in STORE1:
        return "%s(%02x %02x)" % (STORE1[b2], b2, b1)
    if b2 == 0x0F and b1 in (0x28, 0x29, 0x10, 0x11, 0x6E, 0x7E, 0xD6,
                             0x7F, 0x28, 0x29):
        return "sse(%02x %02x %02x)" % (b3, b2, b1)
    # with 66 prefix: [66][0f][modrm][disp]
    if b3 == 0x66 and b2 == 0x0F:
        return "sse66(%02x %02x %02x)" % (b3, b2, b1)
    if b2 in (0x8B, 0x8A):
        return "load(%02x %02x)" % (b2, b1)
    if b2 == 0xF3:
        return "?"
    return ".—(%02x %02x %02x)" % (b3 or 0, b2 or 0, b1 or 0)


want = [int(a, 0) for a in sys.argv[1:]] or OFFS
for off in want:
    pat = struct.pack("<I", off)
    hits = []
    pos = 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        if i < 3:
            continue
        hits.append((VA + i, classify(i)))
    print("== member/room offset +0x%X : %d ==" % (off, len(hits)))
    for va, k in hits[:40]:
        print("   0x%08X  %-16s ctx=%s" % (
            va, k, d[va - VA - 4:va - VA + 8].hex(" ")))
    if len(hits) > 40:
        print("   ... (+%d more)" % (len(hits) - 40))
