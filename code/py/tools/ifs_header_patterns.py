#!/usr/bin/env python3
"""全量解析 .ifs 头部 8 个 u64 的相对关系 + 清单区结构，找规律。"""
import os
import struct
import sys
from collections import Counter


def main():
    root = sys.argv[1]
    files = sorted(f for f in os.listdir(root) if f.endswith(".ifs"))
    pat = Counter()
    samples = {}
    man_kinds = Counter()

    for fn in files:
        p = os.path.join(root, fn)
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            h = f.read(0x400)
        tbl = [struct.unpack_from("<Q", h, 0x0C + i * 8)[0] for i in range(8)]
        tail = struct.unpack_from("<Q", h, 0x4C)[0]

        # 相对关系签名（用与 size / [4] 的差值）
        sig = []
        for i, v in enumerate(tbl):
            if v == tbl[4]:
                sig.append("=4")
            elif v == size:
                sig.append("=L")
            elif v > tbl[4]:
                sig.append(">4")
            elif v == tbl[4] - tail:
                sig.append("4-t")
            else:
                sig.append("o")
        key = tuple(sig[:4]) + (("T4" if tbl[4] + tail == size else "x"),)
        pat[key] += 1
        samples.setdefault(key, fn)

        # 清单区 0xac..tbl[0] 里的东西
        man = h[0xAC:min(0x400, tbl[0] if tbl[0] > 0xAC else 0x400)]
        if b".lst\r\n" in man:
            man_kinds["lst"] += 1
        if b".ff" in man:
            man_kinds["has_ff"] += 1
        if b".iwi" in man:
            man_kinds["has_iwi"] += 1
        if not man.strip(b"\x00"):
            man_kinds["empty"] += 1

    print("头部 8 u64 相对关系签名（[0..3] + T4）:")
    for k, n in pat.most_common(12):
        print("  %-24s %4d   例: %s" % (str(k), n, samples[k][:50]))
    print()
    print("清单区内容:")
    for k, n in man_kinds.most_common():
        print("  %-10s %d" % (k, n))


if __name__ == "__main__":
    main()
