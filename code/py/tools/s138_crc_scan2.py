#!/usr/bin/env python3
"""s138_crc_scan2: 解析客户端"内联 crc32"的字符串常量 (修正版: 允许 mov ecx,eax 间隔)。
序列: 35 FF FF FF 00 (xor eax,0xFFFFFF) [8B C8 (mov ecx,eax)]
      (83 F1 imm8 / 81 E1 FF 00 00 00 / C1 E8 08 / 33 04 8D tab)*
若中途出现 33 14 8D/33 04 8D 等则证明这是 crc32 展开。
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read()
N = len(d)
VA = 0x400000


def parse_from(i):
    out = bytearray()
    tab = None
    while len(out) < 400 and i + 18 <= N:
        if not (d[i] == 0x83 and d[i+1] == 0xF1):
            break
        if not (d[i+3] == 0x81 and d[i+4] == 0xE1 and d[i+5] == 0xFF and d[i+6] == 0 and d[i+7] == 0):
            break
        if not (d[i+8] == 0xC1 and d[i+9] == 0xE8 and d[i+10] == 0x08):
            break
        if not (d[i+11] == 0x33 and d[i+13] == 0x8D):
            break
        t = struct.unpack_from("<I", d, i + 14)[0]
        out.append(d[i+2])
        tab = t
        i += 18
    return bytes(out), i, tab


def main():
    pat = b"\x35\xff\xff\xff\x00"
    pos = 0
    seen = set()
    while True:
        j = d.find(pat, pos)
        if j < 0:
            break
        pos = j + 1
        k = j + len(pat)
        if d[k:k+2] == b"\x8b\xc8":     # mov ecx,eax
            k += 2
        s, end, tab = parse_from(k)
        if not s:
            continue
        key = (s, tab)
        if key in seen:
            continue
        seen.add(key)
        print("0x%08X crc32-table=0x%08X  str=%r" % (j + VA, tab or 0, s.decode("latin1")))
    print("\ncount=%d" % len(seen))


if __name__ == "__main__":
    main()
