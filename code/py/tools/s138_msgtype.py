#!/usr/bin/env python3
"""s138_msgtype: dump 0x7FE980 消息类型跳转表 (type 4..0x15),并反汇编每个分支开头."""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000

def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None

md = Cs(CS_ARCH_X86, CS_MODE_32)
T = 0x7FE980
print("=== jump table @0x7FE980 (idx = type-4, 0..0x11) ===")
for k in range(0x12):
    tgt = u32(T + 4 * k)
    print("  type 0x%02X (%2d) -> 0x%08X" % (k + 4, k + 4, tgt or 0))

print("\n=== 每个分支开头 12 条指令 ===")
seen = set()
for k in range(0x12):
    tgt = u32(T + 4 * k)
    if not tgt or tgt in seen: continue
    seen.add(tgt)
    print("--- type 0x%02X @0x%08X ---" % (k + 4, tgt))
    f = tgt - VA
    cnt = 0
    for ins in md.disasm(d[f:f + 0x60], tgt):
        line = "    0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        print(line)
        cnt += 1
        if cnt >= 10: break
