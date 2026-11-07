# -*- coding: utf-8 -*-
"""E-A 决定性实验: file_offset 是 RVA 还是 VA."""
import struct

IMG = r"E:\codol_re\client_image_20261027.bin"
d = open(IMG, "rb").read()
N = len(d)
BASE = 0x400000


def show(off, lbl):
    print("  %-22s off=0x%08X" % (lbl, off))
    if 0 <= off < N - 32:
        for r in range(0, 32, 16):
            o = off + r
            print("      %08X  %-47s  %s"
                  % (o, d[o:o + 16].hex(" "),
                     "".join(chr(c) if 32 <= c < 127 else "."
                             for c in d[o:o + 16])))
    else:
        print("      OUT OF FILE")


print("=" * 70)
print("E-A: 节 0 首字节位置")
print("=" * 70)
show(0x00001000, "若 file_off = RVA")
show(0x401000, "若 file_off = VA")

print()
print("=" * 70)
print("E-D: 导出表 AddressOfFunctions (RVA 0x00A155D8)")
print("=" * 70)
AF = 0x00A155D8
print("  前 8 个函数 RVA:")
for i in range(8):
    v = struct.unpack_from("<I", d, AF + i * 4)[0]
    print("    [%d] 0x%08X  -> 该 RVA 处: %s"
          % (i, v, d[v:v + 12].hex(" ")))

print()
print("=" * 70)
print("E-E: 反查镜像里出现的指针, 判断到底是 RVA 还是 VA")
print("=" * 70)
# 导入描述符里 Name = 0x0E5DC66D
print("  导入 Name 字段值 = 0x0E5DC66D:")
for cand, lbl in ((0x0E5DC66D, "当 RVA 用"), (0x0E5DC66D - BASE, "当 VA 用")):
    if 0 <= cand < N:
        s = d[cand:cand + 48].split(b"\x00")[0]
        print("    %-12s off=0x%08X -> %r" % (lbl, cand, s))
    else:
        print("    %-12s off=0x%08X -> OUT" % (lbl, cand))

print()
print("  TLS StartOfRawData = 0x0E9C8000:")
for cand, lbl in ((0x0E9C8000, "当 RVA 用"), (0x0E9C8000 - BASE, "当 VA 用")):
    if 0 <= cand < N - 16:
        print("    %-12s off=0x%08X -> %s" % (lbl, cand, d[cand:cand + 16].hex(" ")))
    else:
        print("    %-12s off=0x%08X -> OUT (文件只有 0x%08X)" % (lbl, cand, N))

print()
print("  EXPORT.Name = 0x00A156B4:")
for cand, lbl in ((0x00A156B4, "当 RVA 用"), (0x00A156B4 - BASE, "当 VA 用")):
    if 0 <= cand < N:
        s = d[cand:cand + 48].split(b"\x00")[0]
        print("    %-12s off=0x%08X -> %r" % (lbl, cand, s))
    else:
        print("    %-12s off=0x%08X -> OUT" % (lbl, cand))

print()
print("=" * 70)
print("E-F: 关键 RVA 与 (RVA-BASE) 的字节对照表")
print("=" * 70)
print("  %-28s %-24s %-24s" % ("描述", "RVA 直读", "RVA-BASE 直读"))
for lbl, rva in (("入口点", 0x0E5DC690),
                 ("导出表", 0x00A155B0),
                 ("资源目录", 0x0E5C9000),
                 ("TLS 目录", 0x009E8EB8),
                 ("DEBUG 目录", 0x008ADA60),
                 ("第一 DllName", 0x0E5DC66D)):
    a = d[rva:rva + 12].hex(" ") if 0 <= rva < N - 12 else "OUT"
    b = d[rva - BASE:rva - BASE + 12].hex(" ") if BASE <= rva < N + BASE - 12 else "NEG"
    print("  %-28s %-24s %-24s" % (lbl, a, b))
