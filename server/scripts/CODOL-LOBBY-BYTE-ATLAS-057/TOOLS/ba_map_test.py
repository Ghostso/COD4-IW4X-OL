# -*- coding: utf-8 -*-
"""决定性地址映射测试: file_offset 到底是 RVA 还是 VA-0x400000."""
import struct

IMG = r"E:\codol_re\client_image_20261027.bin"
d = open(IMG, "rb").read()
N = len(d)
BASE = 0x400000


def dump(off, n=0x60, label=""):
    print("--- file offset 0x%08X  %s" % (off, label))
    for r in range(0, n, 16):
        o = off + r
        if o + 16 > N:
            break
        print("    %08X  %-47s  %s"
              % (o, d[o:o + 16].hex(" "),
                 "".join(chr(c) if 32 <= c < 127 else "." for c in d[o:o + 16])))


print("=" * 72)
print("测试 1: 导入描述符 Name 字段 = 0x0E5DC66D. 字符串在哪?")
print("=" * 72)
for cand in (0x0E5DC66D, 0x0E5DC66D - BASE):
    o = cand
    if 0 <= o < N:
        s = d[o:o + 48].split(b"\x00")[0]
        print("  offset 0x%08X -> %r" % (o, s))
    else:
        print("  offset 0x%08X -> OUT OF FILE" % o)

print()
print("=" * 72)
print("测试 2: 入口点. RVA=0x0E5DC690")
print("=" * 72)
dump(0x0E5DC690, 0x40, "file_off = RVA 假设")
print()
dump(0x0E5DC690 - BASE, 0x40, "file_off = RVA-BASE 假设(负偏移?)")

print()
print("=" * 72)
print("测试 3: call [0x0E9DC665] 的槽")
print("=" * 72)
for lbl, off in (("file_off = VA - 0x400000", 0x0E9DC665 - BASE),
                 ("file_off = VA (直接)", 0x0E9DC665)):
    if 0 <= off < N - 4:
        v = struct.unpack_from("<I", d, off)[0]
        print("  %-28s offset 0x%08X -> 0x%08X" % (lbl, off, v))
    else:
        print("  %-28s offset 0x%08X -> OUT" % (lbl, off))

print()
print("=" * 72)
print("测试 4: 两个候选区域的实际内容")
print("=" * 72)
dump(0x0E5DC600, 0xC0, "区域 A")
print()
dump(0x0A9DC600, 0xC0, "区域 B")

print()
print("=" * 72)
print("测试 5: 用 Capstone 反汇编入口点两种解释")
print("=" * 72)
import capstone
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for lbl, off in (("offset 0x0E5DC690", 0x0E5DC690),
                 ("offset 0x0A9DC690", 0x0A9DC690)):
    print("\n  %s:" % lbl)
    n = 0
    for ins in md.disasm(d[off:off + 0x40], BASE + off):
        print("    %08X  %-14s %s %s"
              % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        n += 1
        if n > 8:
            break
    if n == 0:
        print("    (无法反汇编)")
