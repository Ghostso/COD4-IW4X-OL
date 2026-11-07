#!/usr/bin/env python3
"""对 0x6c 做结构假设的穷举验证。

候选 H1: 6c | 08 | u32 N | N 字节 | u32 M | 00
候选 H2: 6c | 08 | u32 N | N 字节 | 00
候选 H3: 6c | u32 N | N 字节 | 00
候选 H4: 6c | 08 | u32 N(元素数) | 4N 字节 | 00
"""
import json
import struct
import sys
from collections import defaultdict


def test(p, h):
    if not p or p[0] != 0x6C:
        return None
    try:
        if h == "H1":
            n = struct.unpack_from("<I", p, 2)[0]
            need = 2 + 4 + n + 4 + 1
            return need == len(p)
        if h == "H2":
            n = struct.unpack_from("<I", p, 2)[0]
            return 2 + 4 + n + 1 == len(p)
        if h == "H3":
            n = struct.unpack_from("<I", p, 1)[0]
            return 1 + 4 + n + 1 == len(p)
        if h == "H4":
            n = struct.unpack_from("<I", p, 2)[0]
            return 2 + 4 + 4 * n + 1 == len(p)
        if h == "H5":  # N 字节 + 一个 u32 + 无终止符
            n = struct.unpack_from("<I", p, 2)[0]
            return 2 + 4 + n + 4 == len(p)
        if h == "H6":  # N 字节 + 无尾
            n = struct.unpack_from("<I", p, 2)[0]
            return 2 + 4 + n == len(p)
    except Exception:
        return False
    return None


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    per = defaultdict(list)
    for r in corpus:
        if r["payload"][:2] == "6c":
            per[(r["svc"], r["task"])].append(bytes.fromhex(r["payload"]))
    for k in sorted(per):
        print("=== %d/%d n=%d lens=%s" % (
            k[0], k[1], len(per[k]), sorted({len(x) for x in per[k]})))
        for h in ("H1", "H2", "H3", "H4", "H5", "H6"):
            cnt = sum(1 for p in per[k] if test(p, h))
            print("   %s hit=%d/%d" % (h, cnt, len(per[k])))


if __name__ == "__main__":
    main()
