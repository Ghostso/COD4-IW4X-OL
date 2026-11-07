#!/usr/bin/env python3
"""验证候选 list-tag 家族: 首字节 (0x60..0x7f), 后面跟 count, 再跟 count 个 u32。

收集 corpus 里所有「以 0x6X 开头」的 payload 形态, 并检查:
   形态 A: X | u8 cnt | cnt*4 B
   形态 B: X | u16 cnt | cnt*4 B
   形态 C: X | u32 cnt | cnt*4 B
   形态 D: X | 08 | u32 n | n B | u32 m   (已知 0x6c)
"""
import json
import struct
import sys
from collections import Counter, defaultdict

FORMS = ("A", "B", "C", "D")


def check(p, tag, form):
    if not p or p[0] != tag:
        return False
    L = len(p)
    try:
        if form == "A":
            n = p[1]
            return 2 + 4 * n == L
        if form == "B":
            n = struct.unpack_from("<H", p, 1)[0]
            return 3 + 4 * n == L
        if form == "C":
            n = struct.unpack_from("<I", p, 1)[0]
            return 5 + 4 * n == L
        if form == "D":
            if p[1] != 0x08:
                return False
            n = struct.unpack_from("<I", p, 2)[0]
            return 6 + n + 4 == L
    except Exception:
        return False
    return False


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    seen = Counter()
    hits = defaultdict(lambda: defaultdict(int))
    for r in corpus:
        p = bytes.fromhex(r["payload"])
        if not p:
            continue
        t = p[0]
        if 0x60 <= t <= 0x7F:
            seen[t] += 1
            for f in FORMS:
                if check(p, t, f):
                    hits[t][f] += 1
    print("首字节在 0x60..0x7f 的 payload:")
    for t, c in sorted(seen.items()):
        print("  %02x  n=%-5d %s" % (t, c, dict(hits[t])))

    # 再看当前未解样本的 6b 位置
    print("\n21/5 / 68/3 / 102/1 / 102/5 首字节分布:")
    for tgt in ("21/5", "68/3", "102/1", "102/5"):
        svc, task = [int(x) for x in tgt.split("/")]
        ps = [bytes.fromhex(r["payload"]) for r in corpus
              if r["svc"] == svc and r["task"] == task]
        print("  %-7s %s" % (tgt, Counter(p[0] for p in ps).most_common(6)))


if __name__ == "__main__":
    main()
