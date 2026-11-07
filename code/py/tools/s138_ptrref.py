#!/usr/bin/env python3
"""138: 全镜像搜某 VA 的所有 4 字节出现（指针/立即数），并分类上下文。
用法: python -X utf8 tools/s138_ptrref.py <VA> [<VA>...]
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

OP1 = {0x68: "push imm32", 0xA1: "mov eax,[abs]", 0xA3: "mov [abs],eax",
       0xB8: "mov eax,imm32", 0xB9: "mov ecx,imm32", 0xBA: "mov edx,imm32",
       0xBB: "mov ebx,imm32", 0xBE: "mov esi,imm32", 0xBF: "mov edi,imm32"}


def cstr(va, maxlen=80):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


for a in sys.argv[1:]:
    tgt = int(a, 0)
    pat = struct.pack("<I", tgt)
    print("=" * 72)
    print("0x%08X 全镜像出现：" % tgt)
    pos = 0
    n = 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        n += 1
        va = VA + i
        pre1 = d[i - 1] if i >= 1 else 0
        pre2 = d[i - 2] if i >= 2 else 0
        lab = ""
        if pre2 == 0x8B and pre1 == 0x05:
            lab = "mov r32,[abs]"
        elif pre2 == 0x89 and pre1 == 0x05:
            lab = "mov [abs],r32  ★写入"
        elif pre2 == 0xC7 and pre1 == 0x05:
            lab = "mov dword[abs],imm32"
        elif pre1 in OP1:
            lab = OP1[pre1]
        elif pre1 == 0xE8:
            lab = "(e8后4字节,非指针)"
        else:
            lab = "数据/指针表"
        ctx = " ".join("%02x" % c for c in d[i - 6:i + 10])
        print("   0x%08X  %-24s ctx: %s" % (va, lab, ctx))
    print("   共 %d 处" % n)
