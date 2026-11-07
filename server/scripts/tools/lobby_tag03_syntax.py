#!/usr/bin/env python3
"""穷举 0x03 组的语法假设, 用未解样本判定。

样本 (全部实测):
  102/1:  08 00 00 00 00 | 08 01 00 00 00 | 03 03 0a 00000000 00000000 00
  102/1b: 08 00 00 00 00 | 08 02 00 00 00 | 03 01 0a 00000000 00000000 | 03 02 0a 00000000 00000000 | 00
  102/5:  08 02 00 00 00 | 03 01 03 02 00
  102/7:  08 32 00 00 00 | (03 01 0a <u32> x N) ...
  68/3:   10 00 | 0a 0e2d4c6b8aa9c8e7 | 10 00 | 03 01 13 08 16000000 ... 00
  68/3b:  10 00 | 0a 0e2d4c6b8aa9c8e7 | 10 00 | 03 02 13 08 00000000 00
  21/5:   08 01 00000000 | 08 00 00000000 | 08 0a 00000000 | 07 abad92d6 | 6b 08 04000000 01 00000000 00000000

候选 G1 (count = 元素数, 元素带 tag):   03 cnt  [elem] * cnt
候选 G2 (count = 字节数, 内是 tag 流):  03 len  <len 字节>
候选 G3 (count = 元素数, 元素=裸 u32):  03 cnt  u32*cnt
候选 G4 (count = 元素数, 元素=tag+裸值): 03 cnt  (tag val)*cnt   [tag 决定值宽]
"""
import json
import struct
import sys
from collections import Counter, defaultdict

SIZED = {0x08: 4, 0x07: 4, 0x06: 2, 0x01: 1, 0x0A: 8}


def try_g1(p, i, cnt):
    for _ in range(cnt):
        if i >= len(p):
            return None
        t = p[i]
        if t in SIZED:
            i += 1 + SIZED[t]
        elif t == 0x10:
            z = p.find(b"\x00", i + 1)
            if z < 0:
                return None
            i = z + 1
        elif t == 0x13:
            if i + 6 > len(p):
                return None
            n = struct.unpack_from("<I", p, i + 2)[0]
            i += 6 + n
        else:
            return None
        if i > len(p):
            return None
    return i


def show(name):
    print("=" * 60)
    print(name)
    print("=" * 60)


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    for tgt in ((102, 1), (102, 5), (102, 7), (68, 3)):
        ps = [bytes.fromhex(r["payload"]) for r in corpus
              if (r["svc"], r["task"]) == tgt]
        ps.sort(key=len)
        show("%d/%d  n=%d  distinct=%d" % (tgt[0], tgt[1], len(ps),
             len({x for x in ps})))
        for p in ps[:2]:
            print("len=%d %s" % (len(p), p.hex(" ")))
            for i in range(len(p)):
                if p[i] == 0x03 and i + 1 < len(p):
                    cnt = p[i + 1]
                    j = try_g1(p, i + 2, cnt)
                    print("  03@%d cnt=%d  G1->%s  (rest=%d)" % (
                        i, cnt, j, (len(p) - j) if j is not None else -1))
                    # G3
                    g3 = i + 2 + 4 * cnt
                    print("                 G3->%s (rest=%d)" % (
                        g3, len(p) - g3))
            print()


if __name__ == "__main__":
    main()
