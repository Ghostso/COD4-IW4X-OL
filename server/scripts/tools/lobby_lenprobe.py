#!/usr/bin/env python3
"""对未解 tag 做算术探针: 拼出 'tag|u32|u32|u32' 的所有组合, 找等于文件长的解。

用途: 判定 0x03 / 0x6c / 其它 tag 是否是「长度前缀」。
"""
import json
import struct
import sys
from collections import Counter


def probes(p):
    n = len(p)
    res = []
    # 对内部每个 4 字节窗口, 尝试各种 (prefix) 组合
    for i in range(0, min(len(p) - 4, 200)):
        v = struct.unpack_from("<I", p, i)[0]
        if v in (n, n - 1, n - 2, n - i, n - i - 1, n - i - 2, n - i - 3):
            res.append((i, v, "4B@%d" % i))
    for i in range(0, min(len(p) - 2, 200)):
        v = struct.unpack_from("<H", p, i)[0]
        if v in (n, n - 1, n - 2, n - i, n - i - 1, n - i - 2, n - i - 3):
            res.append((i, v, "2B@%d" % i))
    for i in range(0, min(len(p), 200)):
        if p[i] == n - i or p[i] == n - i - 1 or p[i] == n - i - 2:
            res.append((i, p[i], "1B@%d" % i))
    return res


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    target = sys.argv[2]
    rs = [bytes.fromhex(r["payload"]) for r in corpus
          if "%d/%d" % (r["svc"], r["task"]) == target]
    print("%s n=%d lens=%s" % (target, len(rs), sorted({len(x) for x in rs})))
    # 只看最短那条做代表
    rs.sort(key=len)
    for p in rs[:3]:
        print("\n--- len=%d" % len(p))
        print("hex:", p.hex())
        for i, v, how in probes(p):
            print("  %-8s off=%-4d val=%-6d (len=%d, len-off=%d)" % (how, i, v, len(p), len(p) - i))


if __name__ == "__main__":
    main()
