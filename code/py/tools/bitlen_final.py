#!/usr/bin/env python3
"""生成最终位长表：循环外 + 循环体×N，并给每类的标签长度序列。"""
import subprocess
import sys

sys.path.insert(0, "tools")
import serialize_extract6 as E  # noqa: E402


def main():
    b = open(E.DUMP, "rb").read()
    rows = E.rows_from_vtable()
    seen_s = set()
    print("%-46s %-8s %-7s %-8s %-6s %s" % (
        "class", "方向", "循环外", "循环体", "环数", "变长"))
    for name, sva, dva in rows:
        for label, va, tc, dc in (("ser", sva, E.WB, E.WD),
                                  ("der", dva, E.RB, E.RD)):
            iv = int(va, 16)
            key = (iv, tc)
            if key in seen_s:
                continue
            seen_s.add(key)
            seq, loops = E.analyze(b, iv, tc, dc)
            if not seq:
                continue
            pre = sum(w for lp, k, w, a, v in seq if isinstance(w, int) and not lp)
            lp_ = sum(w for lp, k, w, a, v in seq if isinstance(w, int) and lp)
            var = any(w is None and k == "data" for lp, k, w, a, v in seq)
            if pre == 0 and lp_ == 0 and not var:
                continue
            print("%-46s %-8s %-7d %-8d %-6d %s" % (
                name, label, pre, lp_, loops,
                "VAR" if var else ""))


if __name__ == "__main__":
    main()
