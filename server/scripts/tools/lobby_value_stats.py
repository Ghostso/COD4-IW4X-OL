#!/usr/bin/env python3
"""统计某个 tag 的「值分布」—— 只统计该 tag 在真实字段位置上的值。

用 v5 解析器完整走一遍, 得到结构化结果, 再按 tag 汇总。
比裸字节扫描准确 (不会把其它块里的同值字节误计)。
"""
import json
import struct
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "tools")
from lobby_grammar_v5 import parse  # noqa: E402


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    vals = defaultdict(Counter)
    where = defaultdict(Counter)
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        ok, elems, _why = parse(b)
        key = "%d/%d" % (r["svc"], r["task"])
        for t, v in elems:
            if t in (0x01, 0x03):
                vals[t][v.hex()] += 1
                where[t][(key, v.hex())] += 1
            elif t in (0x06,):
                vals[t]["%d" % struct.unpack("<H", v)[0]] += 1
                where[t][(key, "%d" % struct.unpack("<H", v)[0])] += 1
            elif t == 0x07:
                vals[t]["%d" % struct.unpack("<i", v)[0]] += 1
            elif t == 0x08:
                vals[t]["%d" % struct.unpack("<I", v)[0]] += 1
            elif t == 0x0A:
                vals[t]["%d" % struct.unpack("<Q", v)[0]] += 1
            elif t == 0x10:
                vals[t]["len%d" % len(v)] += 1
            elif t == 0x13:
                vals[t]["len%d" % len(v)] += 1
            elif t in (0x6B, 0x6C):
                cnt, body = v
                vals[t]["count%d/bytes%d" % (cnt, len(body))] += 1

    for t in sorted(vals):
        c = vals[t]
        print("=== tag %02x  n=%d distinct=%d" % (t, sum(c.values()), len(c)))
        for v, k in c.most_common(14):
            print("    %-24s %d" % (v, k))
        if t in (0x01, 0x03):
            print("    -- 出现位置 --")
            for (kk, vv), n in where[t].most_common(8):
                print("       %-8s val=%-4s %d" % (kk, vv, n))
        print()


if __name__ == "__main__":
    main()
