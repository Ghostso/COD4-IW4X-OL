#!/usr/bin/env python3
"""用 v6 提取器做 tag -> 位宽 的联合分布（ser 侧 + der 侧分别统计）。"""
import collections
import sys

sys.path.insert(0, "tools")
import serialize_extract6 as E  # noqa: E402


def main():
    b = open(E.DUMP, "rb").read()
    rows = E.rows_from_vtable()
    for label, idx, tagc, datc in (("SER", 1, E.WB, E.WD),
                                   ("DER", 2, E.RB, E.RD)):
        pairs = collections.Counter()
        seen = set()
        for name, sva, dva in rows:
            va = int((sva, dva)[idx - 1], 16)
            if va in seen:
                continue
            seen.add(va)
            seq, _ = E.analyze(b, va, tagc, datc)
            cur = None
            for lp, kind, w, at, v in seq:
                if kind == "tag":
                    cur = v
                elif kind == "data" and cur is not None:
                    pairs[(cur, w if w else "VAR")] += 1
                    cur = None
                elif kind == "call":
                    cur = None
        print("=== %s ===" % label)
        for t in sorted({k[0] for k in pairs if k[0] is not None}):
            ws = sorted({k[1] for k in pairs if k[0] == t},
                        key=lambda x: (x == "VAR", x))
            tot = sum(n for k, n in pairs.items() if k[0] == t)
            det = ", ".join("%s×%d" % (w, pairs[(t, w)]) for w in ws)
            print("  tag 0x%02x (%3d 次): %s" % (t, tot, det))
        print()


if __name__ == "__main__":
    main()
