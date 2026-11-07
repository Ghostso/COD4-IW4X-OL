# -*- coding: utf-8 -*-
"""对比各版本 public.result 的尾部 125 个 int32, 看是否随购买/装备变化。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROF = os.path.join(ROOT, "player_profiles")
TARGETS = ["public.result", "public.result.new", "public.result.previous"]


def read_tail(path):
    pub = open(path, "rb").read()
    k = 0
    while k < len(pub):
        t = pub[k]
        if t == 0x0A:
            k += 9
        elif t == 0x08:
            k += 5
        elif t == 0x13:
            ln = struct.unpack_from("<I", pub, k + 2)[0]
            k += 6 + ln
            break
        else:
            return []
    vals = []
    while k + 5 <= len(pub) and pub[k] == 0x07:
        vals.append(struct.unpack_from("<i", pub, k + 1)[0])
        k += 5
    return vals


def main():
    tails = {}
    for fn in TARGETS:
        p = os.path.join(PROF, fn)
        if os.path.exists(p):
            tails[fn] = read_tail(p)
    print("读到的版本: %s" % list(tails))
    for fn, t in tails.items():
        nz = [(i, v) for i, v in enumerate(t) if v]
        print()
        print("%s: %d 项, 非零 %d 项" % (fn, len(t), len(nz)))
        print("  非零: %s" % nz)
    print()
    names = list(tails)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = tails[names[i]], tails[names[j]]
            diff = [(k, a[k], b[k]) for k in range(min(len(a), len(b)))
                    if a[k] != b[k]]
            print("%s vs %s: %d 处不同" % (names[i], names[j], len(diff)))
            for k, x, y in diff[:10]:
                print("   [%d] %d -> %d" % (k, x, y))
    return 0


if __name__ == "__main__":
    sys.exit(main())
