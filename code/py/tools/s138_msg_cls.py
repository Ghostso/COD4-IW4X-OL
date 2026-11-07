#!/usr/bin/env python3
"""s138_msg_cls: 在每种 type 的处理器里找"对象 vtable 赋值"(mov [reg+disp], imm32,
   imm32 在 0xDC0000..0xDD0000, 且 vtable[-1] 是合法 COL), 解出类名。

这是 RTTI 路线: dwRoomMessage 族 = 空类 + vtable; 构造器在处理器里被内联。
对每个 type 列出全部候选, 并注明所在指令地址 + 目标寄存器偏移。
"""
import re
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    if not s or not all(32 <= c < 127 for c in s):
        return None
    return s.decode("latin1")


def rtti(imm):
    f = imm - VA
    if not (0 <= f - 4 < N):
        return None
    col = struct.unpack_from("<I", d, f - 4)[0]
    cf = col - VA
    if not (0 <= cf < N - 4):
        return None
    return cstr(struct.unpack_from("<I", d, cf)[0] + 8)


HANDLERS = {
    0x00: 0x636F02, 0x01: 0x636EBA, 0x02: 0x63495A, 0x03: 0x634AC2,
    0x04: 0x634C3C, 0x05: 0x634D35, 0x06: 0x634F13, 0x07: 0x635399,
    0x08: 0x6354A9, 0x09: 0x63550B, 0x0A: 0x6356B8, 0x0B: 0x636EBA,
    0x0C: 0x6355C2, 0x0D: 0x6357BB, 0x0E: 0x635814, 0x0F: 0x635968,
    0x10: 0x6359FC, 0x11: 0x635E57, 0x12: 0x6361B6, 0x13: 0x635F2C,
    0x14: 0x636336, 0x15: 0x6365A3, 0x16: 0x6367C3, 0x17: 0x6367F5,
    0x18: 0x635D8F, 0x19: 0x636EBA, 0x1A: 0x636291, 0x1B: 0x636715,
    0x1C: 0x635AC3, 0x1D: 0x635B47, 0x1E: 0x635C5B, 0x1F: 0x635BE6,
    0x20: 0x6368A7, 0x21: 0x63693E, 0x22: 0x6369FD, 0x23: 0x636ABE,
    0x24: 0x636B6D, 0x25: 0x634CB3, 0x26: 0x636C1D, 0x27: 0x636CD1,
    0x28: 0x636EBA, 0x29: 0x636EBA, 0x2A: 0x636EBA, 0x2B: 0x6352DC,
    0x2C: 0x634A28, 0x2D: 0x636D7F, 0x2E: 0x636E0A,
}

# 处理器右边界(下一 case 起点 / 公用出口)
BOUNDS = {0x636EBA: 0x636F02, 0x636F02: 0x636F3C}

print("每种 type 的处理器内 'mov [reg+disp], <vtable>' 候选:")
for t in range(0x2F):
    h = HANDLERS[t]
    end = h + 0x200
    # 找最近的 'jmp 0x636f02' 或 'ret' 作为右界
    for ins in md.disasm(d[h - VA:h - VA + 0x400], h):
        if ins.mnemonic.startswith("ret"):
            end = ins.address + ins.size
            break
    hits = []
    for ins in md.disasm(d[h - VA:end - VA], h):
        if ins.mnemonic != "mov":
            continue
        m = re.match(r"(?:dword ptr )?\[([^\]]+)\], (0x[0-9a-f]+)$", ins.op_str)
        if not m:
            continue
        imm = int(m.group(2), 16)
        if 0xDC0000 <= imm < 0xDD0000 and rtti(imm):
            hits.append((ins.address, m.group(1), imm, rtti(imm)))
    if not hits:
        continue
    print("\ntype 0x%02X  处理器 0x%08X" % (t, h))
    for (a, reg, vt, nm) in hits:
        print("   0x%08X  [%s] = 0x%08X  -> %s" % (
            a, reg, vt, nm.replace(".?AV", "").replace("@@", "")))
