#!/usr/bin/env python3
"""136 卷工具 A: 两块纯静态普查.

(1) `and eax,0x8F` (25 8F 00 00 00) 家族的后续 `cmp al,imm8` 取值域
    —— 用来判定 135 的 `(容器.flags & 0x8F)==0x0A` 是不是"类型标签派发".
(2) 全局单例 0xC77BB98 的所有立即数引用(按前置操作码分类)
    —— 找它在哪里被创建(拿到 vtable), 用于给 GFx 转发器 slot 命名.
"""
import re
import struct
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)


def part1():
    print("=" * 74)
    print("(1) `and eax,0x8F` 家族 + 紧随的 cmp al,imm8")
    print("=" * 74)
    vals = Counter()
    hits = []
    for m in re.finditer(rb"\x25\x8f\x00\x00\x00", d):
        i = m.start()
        va = VA + i
        # 向后 12 字节内找 3c XX (cmp al,imm8) 或 24 XX (and al,imm8)
        ctx = d[i + 5:i + 5 + 16]
        cmps = [(k, ctx[k + 1]) for k in range(len(ctx) - 1)
                if ctx[k] == 0x3C and ctx[k + 1] < 0x20]
        for k, v in cmps:
            vals[v] += 1
        hits.append((va, cmps[:2], d[i - 2:i + 10].hex()))
    print("命中 %d 处; 其后 cmp al,imm8 的取值分布: %s" % (
        len(hits), dict(sorted(vals.items()))))
    for va, cmps, ctx in hits[:40]:
        print("  0x%08X  cmp=%s  ctx: %s" % (
            va, ["0x%02X" % v for _, v in cmps], ctx))


def part2():
    print()
    print("=" * 74)
    print("(2) 全局单例 0xC77BB98 的立即数引用")
    print("=" * 74)
    pat = struct.pack("<I", 0x0C77BB98)
    OP = {0x68: "push imm32", 0xA1: "mov eax,[abs]", 0xA3: "mov [abs],eax",
          0xB8: "mov eax,imm32", 0x89: "mov [abs],eax?", 0x8B: "mov r32,[abs]?",
          0xC7: "mov [abs],imm32", 0xFF: "call/jmp [abs]"}
    out = []
    pos = 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        pre = d[i - 1] if i else 0
        pre2 = d[i - 2] if i > 1 else 0
        lab = OP.get(pre, "?")
        # modrm 形式 mov r32,[abs] = 8B 05 xx ; mov [abs],r32 = 89 05 xx
        if pre2 == 0x8B and pre == 0x05:
            lab = "mov r32,[abs]"
        if pre2 == 0x89 and pre == 0x05:
            lab = "mov [abs],r32"
        if pre2 == 0xFF and pre == 0x15:
            lab = "call [abs]"
        if pre2 == 0xFF and pre == 0x25:
            lab = "jmp [abs]"
        out.append((VA + i, lab, d[i - 3:i + 7].hex()))
    print("共 %d 处" % len(out))
    for va, lab, ctx in out:
        print("  0x%08X  %-16s ctx: %s" % (va, lab, ctx))


if __name__ == "__main__":
    part1()
    part2()
