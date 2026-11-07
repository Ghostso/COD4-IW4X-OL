#!/usr/bin/env python3
"""139f: 在 76 项表的各 handler 里找 call [reg+slot]，定位谁调 slot4/6/7/10。
"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
IMG = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(IMG, "rb").read()

OP = {}
base = 0xB83744
for i in range(76):
    OP[i] = struct.unpack_from("<I", d, base - VA + i * 4)[0]

# 唯一 handler 地址，按升序带边界
hs = sorted(set(OP.values()))
print("unique handlers:", len(hs), " range 0x%X..0x%X" % (hs[0], hs[-1]))

SLOTS = {0x10: "slot4  (op9/10 定向)", 0x18: "slot6  (op7/8 广播)", 0x1C: "slot7  (op0x1F)",
         0x28: "slot10 (邀请)", 0x14: "slot5", 0x20: "slot8", 0x24: "slot9"}

print("\n=== call [reg+slot] 命中 ===")
for j, h in enumerate(hs):
    lo = h
    hi = hs[j + 1] if j + 1 < len(hs) else 0xB83744
    off = lo - VA
    n = hi - lo
    for k in range(n - 2):
        if d[off + k] != 0xFF:
            continue
        m = d[off + k + 1]
        # mod=10 (disp32) or mod=01 (disp8): FF /2 = call
        if (m & 0x38) != 0x10:
            continue
        mod = m >> 6
        rm = m & 7
        if mod == 1 and rm != 4:
            disp = d[off + k + 2]
        elif mod == 2 and rm != 4:
            disp = struct.unpack_from("<I", d, off + k + 2)[0]
        elif rm == 4:
            continue
        else:
            continue
        if disp in SLOTS:
            # 反向找哪个 opcode 用它
            ops = [hex(o) for o, v in OP.items() if v == h]
            print(f"  0x{lo+k:08X}  handler 0x{lo:08X} (op {ops})  call [reg+0x{disp:02X}] = {SLOTS[disp]}")
