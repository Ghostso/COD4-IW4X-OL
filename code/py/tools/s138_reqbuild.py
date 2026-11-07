#!/usr/bin/env python3
"""s138_reqbuild: 找 6/5 请求构造点: 'push 8; push 20' / 'push 8; push 0' 组合,
且附近有 push 1 (consume) 与 tag 8. 也搜 mov reg,0x14 附近."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
TL, TH = 0x401000, 0x401000 + 0x8a689a


def near_seqs(i, lo=64, hi=96):
    seg = d[max(0, i - lo):i + hi]
    return seg


print("=== '6a 08 6a 14' / '6a 14 6a 08' 及 '6a 08 6a 00' ===")
for i in range(TL - VA, TH - VA - 8):
    b = d[i:i+4]
    tag = None
    if b[:4] == b"\x6a\x08\x6a\x14": tag = "push8,push20"
    elif b[:4] == b"\x6a\x14\x6a\x08": tag = "push20,push8"
    elif b[:4] == b"\x6a\x08\x6a\x00": tag = "push8,push0"
    if tag:
        seg = near_seqs(i)
        has1 = b"\x6a\x01" in seg
        print("  @VA 0x%08X %-12s has_push1=%s" % (VA + i, tag, has1))

print("\n=== 'push 8; push 20; push 1' 连续或近 ===")
for i in range(TL - VA, TH - VA - 16):
    seq = d[i:i+12]
    # any arrangement
    if b"\x6a\x08" in seq and b"\x6a\x14" in seq:
        seg = d[i:i+24]
        c1 = seg.count(b"\x6a\x01")
        c8 = seg.count(b"\x6a\x08")
        if c1 >= 1:
            print("  @VA 0x%08X bytes=%s push1x%d push8x%d" % (VA + i, seq.hex(), c1, c8))
