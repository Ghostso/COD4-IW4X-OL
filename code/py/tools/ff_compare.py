#!/usr/bin/env python3
"""对比多个 .ff：头同构？载荷熵一致？
若 IWff0100 确实是"已加密且不在此处解密"，那么：
  - 所有 .ff 的载荷都应高熵
  - 头的 8 个 u64 都是随机（不是偏移）
相反，若它是明文，应该能看到低熵区或可读结构。
"""
import os
import struct
import sys
from collections import Counter
import math


def ent(d):
    if not d:
        return 0
    c = Counter(d)
    n = len(d)
    return -sum((v / n) * math.log(v / n, 2) for v in c.values())


def main():
    paths = sys.argv[1:]
    for p in paths:
        b = open(p, "rb").read()
        magic = b[:8]
        ver = struct.unpack_from("<I", b, 8)[0] if len(b) > 12 else -1
        f12 = struct.unpack_from("<I", b, 12)[0] if len(b) > 16 else -1
        f16 = struct.unpack_from("<I", b, 16)[0] if len(b) > 20 else -1
        body = b[20:]
        print("%-52s size=%-8d magic=%-9s ver=%-5d f12=%-3d f16=%-3d ent=%.3f"
              % (os.path.basename(p)[:52], len(b), magic.decode("latin1"), ver,
                 f12, f16, ent(body[:4096]) if body else 0))
        # 逐 4KB 熵
        if len(b) > 8192:
            es = [ent(b[i:i + 4096]) for i in range(0, min(len(b), 6 * 4096), 4096)]
            print("        per-4K: " + " ".join("%.2f" % x for x in es))


if __name__ == "__main__":
    main()
