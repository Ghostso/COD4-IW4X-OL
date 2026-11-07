#!/usr/bin/env python3
"""139c: 找 rec+0x01 (0xE374651) 的写点；形式应为 mov byte [reg+1], imm。
并发 0x7E7910 / 0x7E7936 的调用者 (E8 rel32)。
"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
IMG = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(IMG, "rb").read()
BASE = 0xE374650

def callers(target):
    out = []
    for i in range(len(d) - 5):
        if d[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", d, i + 1)[0]
        if (i + 5 + rel + VA) == target:
            out.append(i + VA)
    return out

for t in (0x7E7910, 0x7E7936, 0x7E7970, 0x7E79C0, 0x7E7A50, 0x7E7C90):
    print(f"callers of 0x{t:08X}: {[hex(x) for x in callers(t)]}")

print("\n=== mov byte [reg+1], imm8 形式扫描 (c6 4x 01 ?? / c6 8x disp32 01) ===")
# 1) ModRM = 0x40|reg  (mod=01, rm=000) → [eax+1]; also 0x41..0x47
hits = []
for i in range(len(d) - 4):
    if d[i] != 0xC6:
        continue
    m = d[i+1]
    if (m & 0xC7) == 0x40 and d[i+2] == 0x01:   # mod=01 rm=0 => [reg+disp8], disp8=1
        hits.append((i + VA, d[i+1] >> 3, d[i+3]))
    elif (m & 0xC7) == 0x80 and d[i+2:i+5] == b"\x01\x00\x00":  # mod=10 [reg+disp32]
        hits.append((i + VA, d[i+1] >> 3, d[i+5]))
print(f"{len(hits)} 处 mov byte [reg+1], imm8")
# 只打印 imm 非 0 的，且在 srpc 附近或操作 0xE374650 附近基址的
for va, reg, imm in hits:
    if imm == 0:
        continue
    if 0x7E7000 <= va <= 0x7E8000 or 0x633000 <= va <= 0x635000 or 0x62C000 <= va <= 0x631000:
        print(f"  0x{va:08X}  reg={reg} imm=0x{imm:02X}")
