#!/usr/bin/env python3
"""房间相关 task 的逐字节全形态枚举：11/2, 11/4, 11/13, 6/5, 6/14。
输出每种形态的完整 hex + 结构化字段。
"""
import json
import sys
from collections import Counter

sys.path.insert(0, "tools")
from lobby_grammar_v5 import parse


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    targets = [(11, 2), (11, 4), (11, 13), (6, 5), (6, 14), (11, 1)]
    for svc, task in targets:
        rs = [r for r in corpus if (r["svc"], r["task"]) == (svc, task)]
        if not rs:
            print("=== %d/%d : 无样本" % (svc, task))
            continue
        print("=" * 78)
        print("=== %d/%d  samples=%d" % (svc, task, len(rs)))
        forms = Counter()
        for r in rs:
            forms[bytes.fromhex(r["payload"])] += 1
        print("  distinct payloads: %d" % len(forms))
        for p, n in forms.most_common(12):
            print("\n  --- x%d  len=%d" % (n, len(p)))
            ok, elems, why = parse(p)
            if not ok:
                print("     parse FAIL: %s" % why)
                print("     hex: %s" % p.hex(" "))
                continue
            for kind, v in elems:
                print("     tag %02x  len=%-4d %s" % (
                    kind, len(v) if v is not None else 0,
                    (v[:40].hex(" ") if isinstance(v, bytes) else v)))
            print("     [tail %d zero bytes]" % (
                len(p) - sum(1 + (len(v) if isinstance(v, bytes) else
                                  (4 + len(v[1]) if kind == 0x6C else 0))
                             for kind, v in elems)))
        print()


if __name__ == "__main__":
    main()
