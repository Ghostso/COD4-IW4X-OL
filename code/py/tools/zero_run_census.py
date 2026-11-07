#!/usr/bin/env python3
"""零串(0x00 run)全景统计：按串长 × 前字节 × 后字节分类，
并把每一类映射回 TLV 文法，回答"这个零串是什么结构"。

用法:
  python -I tools/zero_run_census.py corpus out
"""
import collections
import json
import re
import sys


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    out = open(sys.argv[2], "w", encoding="utf-8")

    def w(s=""):
        print(s)
        out.write(s + "\n")

    n_rec = len(corpus)
    tot_b = 0
    tot_z = 0
    last_is_zero = 0
    first_hist = collections.Counter()
    run_by_len = collections.defaultdict(collections.Counter)
    len_hist = collections.Counter()

    for r in corpus:
        b = bytes.fromhex(r["payload"])
        n = len(b)
        tot_b += n
        tot_z += b.count(0)
        first_hist[b[0]] += 1
        if b and b[-1] == 0:
            last_is_zero += 1
        for m in re.finditer(b"\x00+", b):
            L = len(m.group())
            s, e = m.start(), m.end()
            pre = b[s - 1] if s > 0 else None
            post = b[e] if e < n else None
            at_end = (e == n)
            run_by_len[L][(pre, post, at_end)] += 1
            len_hist[L] += 1

    w("=== 零串全景 (corpus=%d, bytes=%d, zeros=%d, %.3f%%) ===" % (
        n_rec, tot_b, tot_z, 100.0 * tot_z / tot_b))
    w("★ 末字节为 0x00 的 payload: %d / %d (%.2f%%)" % (
        last_is_zero, n_rec, 100.0 * last_is_zero / n_rec))
    w("首字节分布: " + ", ".join(
        "%02x:%d" % (k, v) for k, v in first_hist.most_common(10)))
    w("")
    w("=== 按串长 (len: 出现次数) ===")
    for L in sorted(len_hist):
        w("  len=%-3d  %d" % (L, len_hist[L]))
    w("")
    for L in sorted(run_by_len):
        c = run_by_len[L]
        tot = sum(c.values())
        w("--- 零串 len=%d (共 %d) ---" % (L, tot))
        for (pre, post, at_end), k in c.most_common(8):
            f = lambda x: ("END" if x is None else "%02x" % x)
            w("    %s <00x%d> %s %s  ×%d" % (
                f(pre), L, f(post), "[尾]" if at_end else "", k))
    out.close()


if __name__ == "__main__":
    main()
