#!/usr/bin/env python3
"""6/14 内层文本命令的完整字段化。
枚举所有 mmstart / mmbook / mmban 变体，按 ';' 与空格切分，统计每个位置。"""
import json
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "tools")
from lobby_grammar_v5 import parse


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    rs = [r for r in corpus if (r["svc"], r["task"]) == (6, 14)]
    bodies = Counter()
    for r in rs:
        p = bytes.fromhex(r["payload"])
        ok, elems, _ = parse(p)
        if not ok:
            continue
        u64 = None
        for k, v in elems:
            if k == 0x0A:
                u64 = v
            elif k == 0x13:
                bodies[(u64, v)] += 1

    print("6/14 distinct (u64, body) =", len(bodies))
    # 按 u64 分组
    by_u64 = defaultdict(list)
    for (u, b), n in bodies.items():
        by_u64[u].append((b, n))

    for u, lst in by_u64.items():
        print("\n" + "=" * 74)
        print("u64 = 0x%s" % (u.hex() if u else "?"))
        for b, n in sorted(lst, key=lambda x: -x[1])[:14]:
            print("  x%-4d len=%-4d %r" % (n, len(b), b[:120]))

    print("\n" + "=" * 74)
    print("mmstart 命令的字段切分（按 ';'）：")
    fields = Counter()
    for (u, b), n in bodies.items():
        if not b.startswith(b"mmstart"):
            continue
        for part in b.decode("latin1").split(";"):
            part = part.strip()
            if part:
                fields[(part.split()[0] if part.split() else "?",
                        part)] += n
    # 按键名归组
    keys = defaultdict(Counter)
    for (k, full), n in fields.items():
        keys[k][full] += n
    for k in sorted(keys):
        print("  --- %s" % k)
        for full, n in keys[k].most_common(6):
            print("      x%-4d %r" % (n, full[:110]))


if __name__ == "__main__":
    main()
