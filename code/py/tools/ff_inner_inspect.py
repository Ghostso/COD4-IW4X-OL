#!/usr/bin/env python3
"""检查解密后的 .ff 明文内部：找压缩头、找分块边界、逐块熵。"""
import sys
from collections import Counter
import math


def ent(d):
    if not d:
        return 0.0
    c = Counter(d)
    n = len(d)
    return -sum((v / n) * math.log(v / n, 2) for v in c.values())


def main():
    p = sys.argv[1]
    b = open(p, "rb").read()
    print("len=%d" % len(b))
    print("head 32: %s" % b[:32].hex(" "))
    print("repr   : %r" % b[:32])

    # 前 32 字节结构
    import struct
    for i in range(0, 32, 4):
        print("  +%02d u32=%#x (%d)" % (i, struct.unpack_from("<I", b, i)[0],
                                        struct.unpack_from("<I", b, i)[0]))

    print("\n逐 4096 块熵与可打印率：")
    for k in range(0, min(len(b), 40 * 4096), 4096):
        seg = b[k:k + 4096]
        pr = sum(1 for c in seg if 32 <= c < 127 or c in (9, 10, 13))
        print("  %#08x  ent=%.2f  printable=%.1f%%" % (
            k, ent(seg), 100.0 * pr / len(seg)))

    # 找 zlib
    import zlib
    found = 0
    for i in range(len(b) - 2):
        if b[i] == 0x78 and b[i + 1] in (0x01, 0x9C, 0xDA):
            try:
                d = zlib.decompressobj().decompress(b[i:])
                if len(d) > 200:
                    print("\n★ zlib @%#x -> %d 字节" % (i, len(d)))
                    print("  %r" % d[:200])
                    found += 1
                    if found > 5:
                        break
            except Exception:
                pass
    if not found:
        print("\n未找到可解压的 zlib 流")


if __name__ == "__main__":
    main()
