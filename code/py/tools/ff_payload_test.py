#!/usr/bin/env python3
"""对 .ff 载荷做多假设验证：加密 / 压缩 / 明文。

不用外部常量。只用可证伪的断言：
  H1 若是 zlib：能解压
  H2 若是加密：熵接近 8 且无重复块
  H3 若是明文：应出现常见字串（"common"、"menu"、"gsc"…）
  H4 若块大小 0x4000：看每块是否有独立校验
"""
import math
import sys
from collections import Counter


def entropy(buf):
    if not buf:
        return 0.0
    c = Counter(buf)
    n = len(buf)
    e = 0.0
    for v in c.values():
        p = v / n
        e -= p * math.log(p, 2)
    return e


def main():
    path = sys.argv[1]
    off = int(sys.argv[2], 0)
    n = int(sys.argv[3], 0) if len(sys.argv) > 3 else 1 << 20
    b = open(path, "rb").read(off + n)[off:]
    print("payload bytes: %d" % len(b))
    print("entropy: %.4f" % entropy(b))

    # 熵按 4KB 分块，看是否均匀
    block = 4096
    ebs = []
    for i in range(0, len(b) - block, block):
        ebs.append(entropy(b[i:i + block]))
    if ebs:
        print("per-4KB entropy: min=%.3f max=%.3f avg=%.3f" % (
            min(ebs), max(ebs), sum(ebs) / len(ebs)))

    # zlib / gzip
    import zlib
    for name, fn in (("zlib", zlib.decompress),
                     ("raw-deflate", lambda x: zlib.decompressobj(-15).decompress(x))):
        try:
            fn(b)
            print("H1 %-12s OK  <<<< 能解压" % name)
        except Exception as e:
            print("H1 %-12s fail (%s)" % (name, str(e)[:50]))

    # 明文关键词
    kws = [b"common", b"menu", b"gsc", b"UI_", b"frontEnd", b"lobby",
           b"GSC ", b"zone", b"asset", b"IWff"]
    found = [(k, b.count(k)) for k in kws if b.count(k)]
    print("H3 明文关键词:", found if found else "无")

    # 4 字节重复块
    cw = Counter(b[i:i + 4] for i in range(0, len(b) - 4, 4))
    rep = sum(1 for v in cw.values() if v > 1)
    print("H2 重复 4B 词数: %d / %d" % (rep, len(cw)))

    # 全零/全 FF 块
    z = b.count(0)
    f = b.count(0xFF)
    print("   0x00: %.2f%%   0xFF: %.2f%%" % (100 * z / len(b), 100 * f / len(b)))


if __name__ == "__main__":
    main()
