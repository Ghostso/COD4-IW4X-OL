#!/usr/bin/env python3
"""对 corpus 里每个 (svc,task) 做「逐字节位点统计」:
   相同长度 / 相同结构的样本里, 第 i 字节在多少样本中取值相同、取值集合多大。

这是字节级论文的第一手证据: 常量字节 = 结构, 变化字节 = 数据。
"""
import json
import sys
from collections import defaultdict, Counter


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    target = sys.argv[2] if len(sys.argv) > 2 else None
    per = defaultdict(list)
    for r in corpus:
        per[(r["svc"], r["task"])].append(bytes.fromhex(r["payload"]))

    for k in sorted(per):
        if target and target != "%d/%d" % k:
            continue
        ps = [p for p in per[k] if p]
        bylen = defaultdict(list)
        for p in ps:
            bylen[len(p)].append(p)
        print("=== %d/%d samples=%d lens=%s" % (
            k[0], k[1], len(ps),
            ",".join("%d:%d" % (L, len(v)) for L, v in sorted(bylen.items()))))
        # 取样本最多的那个长度做逐字节
        L, grp = max(bylen.items(), key=lambda kv: len(kv[1]))
        n = len(grp)
        out = []
        for i in range(L):
            vals = Counter(p[i] for p in grp)
            if len(vals) == 1:
                out.append((i, "CONST", "%02x" % next(iter(vals)), n))
            else:
                top = vals.most_common(3)
                out.append((i, "VAR", " ".join("%02x×%d" % (v, c) for v, c in top), len(vals)))
        for i, kind, s, extra in out:
            print("  %04x %-5s %-28s %s" % (i, kind, s, extra if kind == "VAR" else ""))
        print()


if __name__ == "__main__":
    main()
