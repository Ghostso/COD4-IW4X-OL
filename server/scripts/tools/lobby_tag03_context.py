#!/usr/bin/env python3
"""抽取 corpus 里所有 0x03 tag 的上下文, 归纳其语法。"""
import json
import sys
from collections import Counter


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    ctx = Counter()
    nxt = Counter()
    samples = {}
    for r in corpus:
        p = bytes.fromhex(r["payload"])
        key = "%d/%d" % (r["svc"], r["task"])
        for i, c in enumerate(p):
            if c == 0x03:
                nxt[p[i + 1] if i + 1 < len(p) else -1] += 1
                seg = p[i:i + 14].hex()
                ctx[seg[:20]] += 1
                samples.setdefault((key, p[i + 1] if i + 1 < len(p) else -1), seg)
    print("byte after 0x03 (top):")
    for v, c in nxt.most_common(12):
        print("  %-4s %d" % ("%02x" % v if v >= 0 else "EOF", c))
    print()
    print("distinct 0x03 contexts (top 25):")
    for s, c in ctx.most_common(25):
        print("  %-22s %d" % (s, c))
    print()
    print("per svc/task, next-byte:")
    for (key, nb), seg in sorted(samples.items()):
        print("  %-8s next=%-4s %s" % (key, "%02x" % nb if nb >= 0 else "EOF", seg))


if __name__ == "__main__":
    main()
