#!/usr/bin/env python3
"""11/4 内层是位域还是字节域？做三项判别：
1. 非零字节位置是否呈固定周期性
2. 相同位置跨样本是否恒定
3. 与已知的 Cod 位流（MSB-first）解出来的东西对比
"""
import json
import struct
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "tools")
from lobby_grammar_v5 import parse


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    rs = [r for r in corpus if (r["svc"], r["task"]) == (11, 4)]
    blobs = []
    for r in rs:
        p = bytes.fromhex(r["payload"])
        ok, elems, _ = parse(p)
        if not ok:
            continue
        for k, v in elems:
            if k == 0x13:
                blobs.append(v)
                break

    # 按 hdr 分组
    groups = defaultdict(list)
    for b in blobs:
        if len(b) >= 8 and b[4] == 2:
            groups[b[5]].append(b)

    for h in sorted(groups):
        g = groups[h]
        print("=" * 70)
        print("hdr=02 %02x  n=%d  lens=%s" % (h, len(g),
                                             sorted({len(x) for x in g})))
        # 取最常见的那个长度
        L = Counter(len(x) for x in g).most_common(1)[0][0]
        same = [x for x in g if len(x) == L]
        print("  同长度样本 %d 个 (len=%d)" % (len(same), L))
        # 逐字节恒定/变化
        const, var = [], []
        for i in range(L):
            vals = {x[i] for x in same}
            if len(vals) == 1:
                const.append((i, next(iter(vals))))
            else:
                var.append((i, len(vals)))
        print("  恒定字节 %d 个: %s" % (
            len(const), " ".join("%d:%02x" % (i, v) for i, v in const[:40])))
        print("  变化字节 %d 个: 前 20 位置 %s" % (
            len(var), [i for i, _ in var[:20]]))
        print()


if __name__ == "__main__":
    main()
