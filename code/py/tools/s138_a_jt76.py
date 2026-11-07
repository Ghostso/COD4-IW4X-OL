#!/usr/bin/env python3
"""s138_a_jt76: dump the 76-entry jump table at 0xB83744 (opcode 1..0x4B, index=opcode-1).
Each entry -> target address. Print raw dwords plus target bytes.
Usage: python -I tools/s138_a_jt76.py [tableVA]
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

T = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0xB83744


def u32(va):
    o = va - VA
    if 0 <= o <= N - 4:
        return struct.unpack_from("<I", d, o)[0]
    return None


def cstr(va, ml=80):
    o = va - VA
    if not (0 <= o < N - 1):
        return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2:
        return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


print("table base 0x%08X" % T)
rows = []
for k in range(76):
    v = u32(T + 4 * k)
    rows.append(v)

# check sortedness / monotonic
print("first 8:", " ".join("0x%08X" % (x or 0) for x in rows[:8]))
mono = all(rows[i] is not None and rows[i - 1] is not None and rows[i] >= rows[i - 1]
           for i in range(1, 76))
print("monotonic ascending:", mono)
for k in range(76):
    op = k + 1
    v = rows[k]
    prefix = d[(v - VA):(v - VA) + 16].hex(" ") if v and 0 <= v - VA < N else ""
    print("op %2d (0x%02X) idx %2d -> 0x%08X  %s" % (op, op, k, v or 0, prefix))

print("\n--- context before table ---")
for off in range(-0x20, 8, 4):
    v = u32(T + off)
    print("  0x%08X: 0x%08X" % (T + off, v or 0))
