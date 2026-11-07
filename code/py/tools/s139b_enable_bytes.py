#!/usr/bin/env python3
"""139b: 找 rec+0x00 / rec+0x01 (0xE374650 / 0xE374651) 的写点。
扫描全镜像里所有引用 0xE374650 附近的指令，按寻址形态分类。
"""
import struct, sys, re

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
IMG = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(IMG, "rb").read()

TARGETS = {
    0xE374650: "rec+0x00 enable#1",
    0xE374651: "rec+0x01 enable#2",
    0xE374648: "rec+0x00-8",
    0xE374660: "rec+0x10 key.lo",
    0xE374664: "rec+0x14 key.hi",
    0xE374648 + 0x25C8 - 8: "?",  # placeholder
}
TARGETS = {0xE374650: "rec+0x00", 0xE374651: "rec+0x01",
           0xE374660: "rec+0x10", 0xE374664: "rec+0x14",
           0xE37B7A8: "table end", 0xE376C08: "base op7/8",
           0xE376C0C: "base op9/10"}

FILESZ = len(d)

def read(off, n):
    return d[off:off+n]

def find_all(pat):
    out, i = [], 0
    while True:
        j = d.find(pat, i)
        if j < 0:
            break
        out.append(j)
        i = j + 1
    return out

print("=== 1) 直接 disp32 引用 (mov [imm32], ... / cmp [imm32], ...) ===")
for va, name in TARGETS.items():
    pat = struct.pack("<I", va)
    hits = find_all(pat)
    print(f"\n-- {name} @0x{va:08X}: {len(hits)} 处 dword 出现")
    for off in hits[:40]:
        ctx = d[max(0, off-12): off+16]
        # 往前找指令起始附近
        print(f"   file 0x{off:08X}  VA 0x{off+VA:08X}  ctx={' '.join(f'{b:02x}' for b in ctx)}")

print("\n=== 2) 结构体基址 0xE374650 的 disp32 (含 +小偏移) ===")
base_hits = find_all(struct.pack("<I", 0xE374650))
print(f"基址出现 {len(base_hits)} 处")
for off in base_hits:
    print(f"   file 0x{off:08X} VA 0x{off+VA:08X}")
