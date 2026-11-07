#!/usr/bin/env python3
"""s137: 在镜像里找立即数 932 / 0x3A4 及其它候选值的出现位置(区分代码 imm32 vs 数据)."""
import struct
import sys

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

# 节表: 简单取 .text/.rdata/.data 范围可先不取, 直接统计所有出现并标注前导字节.
def scan(v):
    pat = struct.pack("<I", v)
    hits = []
    off = 0
    while True:
        i = d.find(pat, off)
        if i < 0:
            break
        off = i + 1
        hits.append(i)
    return hits

for v in [int(x, 0) for x in (sys.argv[1:] or ["932", "0x64", "0x65", "0x3EC"])]:
    hits = scan(v)
    print("=== imm32 0x%08X (%d) : %d 处 ===" % (v, v, len(hits)))
    # 分: 代码候选(前导字节是 push/mov/cmp 等) vs 数据
    code = []
    for i in hits:
        if i < 2:
            continue
        op = d[i - 1]
        # opcode 前缀判断
        if op in (0x68, 0xB8, 0xB9, 0xBA, 0xBB, 0xBE, 0xBF, 0x6A) or (d[i - 2] in (0xC7, 0x81, 0x3D, 0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D)):
            code.append(i)
    print("  代码候选 imm32: %d" % len(code))
    for i in code[:25]:
        print("    file=0x%08X VA=0x%08X ctx=%s" % (i - 3, VA + i - 3, " ".join("%02x" % c for c in d[i - 3:i + 7])))
    # 连续表: 检查 i-4 与 i+4 是否也是小整数递增
    print("  数据出现(前 12): " + ", ".join("0x%08X" % (VA + i) for i in hits[:12]))
