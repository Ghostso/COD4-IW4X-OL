#!/usr/bin/env python3
"""s138_type_cls: 每种 type 的反序列化器内部 `mov dword ptr [reg], <vtable>` 的
   最后一条 = 最派生类 vtable; 经 vtable[-4]=COL -> COL[0]=TI -> TI+8=RTTI 名。

已在 0x625940 上人工确认: `c706e07bdc00` = mov dword ptr [esi], 0xdc7be0,
   `c7060475dc00` = mov dword ptr [esi], 0xdc7504  -> dwRoomMessageText。
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


def rtti_of(vt):
    """MSVC: vftable[-4]=COL, COL+0x0C=type_info*, type_info+8=修饰名"""
    col = struct.unpack_from("<I", d, vt - VA - 4)[0]
    ti = struct.unpack_from("<I", d, col - VA + 0x0C)[0]
    nm = cstr(ti + 8)
    return (col, ti, nm) if nm and nm.startswith(".?AV") else (col, ti, None)


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

MOVVT = re.compile(r"\[(.+?)\], (0x[0-9a-f]+)$")


def func_len(va, maxlen=0x1000):
    for ins in md.disasm(d[va - VA:va - VA + maxlen], va):
        if ins.mnemonic.startswith("ret"):
            return ins.address + ins.size - va
    return maxlen


def scan(va):
    """返回该函数(到第一个 ret)内所有 vtable 立即数写入"""
    out = []
    for ins in md.disasm(d[va - VA:va - VA + func_len(va)], va):
        if ins.mnemonic == "mov":
            m = MOVVT.search(ins.op_str)
            if m:
                imm = int(m.group(2), 16)
                if 0xDC0000 <= imm < 0xDD0000:
                    out.append((ins.address, m.group(1), imm))
    return out


DESERS = {
    0x02: 0x625940, 0x04: 0x625DB0, 0x05: 0x626B30, 0x06: 0x627230,
    0x07: 0x627B40, 0x08: 0x627CE0, 0x09: 0x627B40, 0x0A: 0x626130,
    0x0C: 0x625F50, 0x0E: 0x627E00, 0x0F: 0x627EE0, 0x10: 0x629090,
    0x11: 0x625DB0, 0x12: 0x628B90, 0x13: 0x6280B0, 0x14: 0x628260,
    0x15: 0x625DB0, 0x16: 0x6284E0, 0x17: 0x628610, 0x18: 0x6268A0,
    0x1A: 0x625DB0, 0x1B: 0x6283C0, 0x1C: 0x626730, 0x1D: 0x6263C0,
    0x1E: 0x625DB0, 0x1F: 0x627CE0, 0x20: 0x629020, 0x21: 0x629090,
    0x22: 0x6291B0, 0x23: 0x625DB0, 0x24: 0x625DB0, 0x25: 0x6269E0,
    0x26: 0x628740, 0x27: 0x629090, 0x2B: 0x627C30, 0x2C: 0x625AB0,
    0x2D: 0x629090, 0x2E: 0x629090,
}

print("== 反序列化器构造器 vtable 扫描 ==")
for t in sorted(DESERS):
    de = DESERS[t]
    res = []
    for a, reg, imm in scan(de):
        col, ti, nm = rtti_of(imm)
        if nm:
            res.append((a, reg, imm, nm.replace(".?AV", "").replace("@@", "")))
    if not res:
        print("type 0x%02X deser 0x%08X : (无 vtable 内联)" % (t, de))
        continue
    print("type 0x%02X handler 0x%08X deser 0x%08X:" % (t, HANDLERS[t], de))
    for a, reg, imm, nm in res:
        print("   0x%08X  mov [%s], 0x%08X  -> %s" % (a, reg, imm, nm))
