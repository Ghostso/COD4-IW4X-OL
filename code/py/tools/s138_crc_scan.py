#!/usr/bin/env python3
"""s138_crc_scan: 扫描代码里"内联 crc32"的字符串常量。

客户端把 crc32 展平成: xor eax,0xFFFFFF; 然后反复 [xor ecx,imm8; and ecx,0xff; shr eax,8;
xor eax,[ecx*4+TABLE]]; 最后 not eax。
本工具顺序解析每个 crc32 常量,还原被哈希的字符串字面量,并输出 (str -> crc32)。
可用来反查 21 层里 A(0xD692ADAB)/B(0x8D51E398) 等是否来自某个字面量。
"""
import re
import struct
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read()
N = len(d)
VA = 0x400000
TL = 0x401000 - VA
TH = 0x401000 + 0x8a689a - VA

# 常见 crc32 表基址 (前向引用)
TABLES = [0x81FE0C8, 0x0D30450, 0x0DA2D40]


def parse_seq(off, maxn=200):
    """off 指向 'xor eax,0xFFFFFF' 之后(即 0x35 ff ff ff 00 的结尾字节之后)。
    返回 (bytes, end_off, table_va)。"""
    out = bytearray()
    i = off
    tab = None
    while len(out) < maxn and i + 10 < N:
        # 期望 83 f1 xx  81 e1 ff 00 00 00  c1 e8 08  33 04 8d TTTTTTTT
        if d[i] != 0x83 or d[i+1] != 0xF1:
            break
        b = d[i+2]
        if d[i+3] != 0x81 or d[i+4] != 0xE1 or d[i+5] != 0xFF or d[i+6] != 0 or d[i+7] != 0:
            break
        if d[i+8] != 0xC1 or d[i+9] != 0xE8 or d[i+10] != 0x08:
            break
        # 33 04 8d TTTTTTTT
        if d[i+11] != 0x33 or d[i+12] != 0x04 or d[i+13] != 0x8D:
            break
        tva = struct.unpack_from("<I", d, i+14)[0]
        i += 18
        out.append(b)
        tab = tva
    return bytes(out), i, tab


def main():
    pat = b"\x35\xff\xff\xff\x00"   # xor eax,0xFFFFFF
    hits = []
    pos = 0
    while True:
        j = d.find(pat, max(pos, TL), TH)
        if j < 0:
            break
        pos = j + 1
        s, end, tab = parse_seq(j + 5)
        if not s:
            continue
        # 反向: 上一段可能是 mov eax,[0x81fe304] 或 xor eax 结果=前一段; 简化: 只报字符串
        try:
            st = s.decode("latin1")
        except Exception:
            st = "?"
        hits.append((j + VA, st, tab))
    # 去重显示
    seen = set()
    for va, st, tab in hits:
        key = (st, tab)
        if key in seen:
            continue
        seen.add(key)
        print("0x%08X  tab=0x%08X  str=%r" % (va, tab or 0, st))


if __name__ == "__main__":
    main()
