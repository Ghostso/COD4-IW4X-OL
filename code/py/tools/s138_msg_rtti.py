#!/usr/bin/env python3
"""s138_msg_rtti: 对每种 type 的处理函数/反序列化器, 找出它构造的对象 vtable
   (`mov dword ptr [reg], 0xDCxxxx` / `mov dword ptr [reg+N], 0xDCxxxx`),
   再经 COL->RTTI 解出 C++ 类名。

用法: s138_msg_rtti.py [--all]
   默认只报前一层; --all 递归进嵌套子消息。
"""
import re
import sys
import struct
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


def rtti_of_vtable(vt):
    """vtable[-4] = COL, COL+0 = type_info*, type_info+8 = 修饰名"""
    f = vt - VA
    if not (0 <= f - 4 < N):
        return None, None
    col = struct.unpack_from("<I", d, f - 4)[0]
    cf = col - VA
    if not (0 <= cf < N - 4):
        return None, None
    ti = struct.unpack_from("<I", d, cf)[0]
    tf = ti - VA
    if not (0 <= tf + 8 < N):
        return None, None
    return col, cstr(ti + 8)


# 处理函数 -> 反序列化器 (已知映射)
HANDLERS = {
    0x00: (0x636F02, None), 0x01: (0x636EBA, None), 0x02: (0x63495A, 0x625940),
    0x03: (0x634AC2, None), 0x04: (0x634C3C, 0x625DB0), 0x05: (0x634D35, 0x626B30),
    0x06: (0x634F13, 0x627230), 0x07: (0x635399, 0x627B40), 0x08: (0x6354A9, 0x627CE0),
    0x09: (0x63550B, 0x627B40), 0x0A: (0x6356B8, 0x626130), 0x0B: (0x636EBA, None),
    0x0C: (0x6355C2, 0x625F50), 0x0D: (0x6357BB, "inline"), 0x0E: (0x635814, 0x627E00),
    0x0F: (0x635968, 0x627EE0), 0x10: (0x6359FC, 0x629090), 0x11: (0x635E57, 0x625DB0),
    0x12: (0x6361B6, 0x628B90), 0x13: (0x635F2C, 0x6280B0), 0x14: (0x636336, 0x628260),
    0x15: (0x6365A3, 0x625DB0), 0x16: (0x6367C3, 0x6284E0), 0x17: (0x6367F5, 0x628610),
    0x18: (0x635D8F, 0x6268A0), 0x19: (0x636EBA, None), 0x1A: (0x636291, 0x625DB0),
    0x1B: (0x636715, 0x6283C0), 0x1C: (0x635AC3, 0x626730), 0x1D: (0x635B47, 0x6263C0),
    0x1E: (0x635C5B, 0x625DB0), 0x1F: (0x635BE6, 0x627CE0), 0x20: (0x6368A7, 0x629020),
    0x21: (0x63693E, 0x629090), 0x22: (0x6369FD, 0x6291B0), 0x23: (0x636ABE, 0x625DB0),
    0x24: (0x636B6D, 0x625DB0), 0x25: (0x634CB3, 0x6269E0), 0x26: (0x636C1D, 0x628740),
    0x27: (0x636CD1, 0x629090), 0x28: (0x636EBA, None), 0x29: (0x636EBA, None),
    0x2A: (0x636EBA, None), 0x2B: (0x6352DC, 0x627C30), 0x2C: (0x634A28, 0x625AB0),
    0x2D: (0x636D7F, 0x629090), 0x2E: (0x636E0A, 0x629090),
}

def callees(va, length=0x600):
    out = []
    for ins in md.disasm(d[va - VA:va - VA + length], va):
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16)
            if 0x400000 <= t < 0xE00000:
                out.append(t)
        if ins.mnemonic.startswith("ret"):
            break
    return out


def func_end(va, maxlen=0x800):
    for ins in md.disasm(d[va - VA:va - VA + maxlen], va):
        if ins.mnemonic.startswith("ret"):
            return ins.address + ins.size - va
    return maxlen


def vtables_in(va):
    """扫 'mov [reg], imm32' 且 imm32 落在 0xDC0000..0xDD0000"""
    length = func_end(va)
    out = []
    for ins in md.disasm(d[va - VA:va - VA + length], va):
        if ins.mnemonic != "mov":
            continue
        m = re.match(r"(?:dword ptr )?\[(.+)\], (0x[0-9a-f]+)$", ins.op_str)
        if not m:
            continue
        imm = int(m.group(2), 16)
        if 0xDC0000 <= imm < 0xDD0000:
            out.append((ins.address, m.group(1), imm))
    return out


def main():
    print("| type | 处理函数 | 反序列化器 | 对象 vtable | C++ 类名 |")
    print("|------|----------|-----------|-------------|----------|")
    for t in range(0x2F):
        h, de = HANDLERS[t]
        if de is None:
            print("| 0x%02X | 0x%08X | (无/空) | - | - |" % (t, h))
            continue
        deser = 0 if de == "inline" else de
        scan = [h] if de == "inline" else [deser, h]
        # 反序列化器 + 它的直接 callee(构造函数) + 处理器
        nodes = list(scan)
        for s in list(scan):
            nodes.extend(callees(s))
        found = []
        for n in nodes:
            found.extend(vtables_in(n))
        good = [(a, r, v) for (a, r, v) in found
                if rtti_of_vtable(v)[1] is not None]
        if not good:
            print("| 0x%02X | 0x%08X | 0x%08X | (未找到) | ? |" % (t, h, deser))
            continue
        addr, reg, vt = good[-1]          # 最后写 = 最派生类
        col, name = rtti_of_vtable(vt)
        print("| 0x%02X | 0x%08X | 0x%08X | 0x%08X | %s |" % (
            t, h, deser, vt, name.replace(".?AV", "").replace("@@", "")))


main()
