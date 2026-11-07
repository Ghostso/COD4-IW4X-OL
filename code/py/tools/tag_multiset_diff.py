#!/usr/bin/env python3
"""对 RoomInfo / Join 两个 DIFF 类做标签多重集对比，定位差异的精确性质。"""
import collections
import sys

sys.path.insert(0, "tools")
import serialize_extract6 as E  # noqa: E402

TARGETS = {
    "dwRoomMessageRoomInfo": (0x627ea0, 0x627ee0),
    "dwRoomMessageJoin": (0x626a80, 0x626b30),
}


def tags(b, va, tagc, datc):
    seq, _ = E.analyze(b, va, tagc, datc)
    return [v for lp, k, w, a, v in seq if k == "tag"]


def main():
    b = open(E.DUMP, "rb").read()
    for name, (sva, dva) in TARGETS.items():
        s = tags(b, sva, E.WB, E.WD)
        d = tags(b, dva, E.RB, E.RD)
        cs, cd = collections.Counter(s), collections.Counter(d)
        print("===== %s =====" % name)
        print("  ser 标签数 %d : %s" % (len(s), dict(sorted(cs.items()))))
        print("  der 标签数 %d : %s" % (len(d), dict(sorted(cd.items()))))
        print("  多重集差 ser-der:", {hex(k): v for k, v in (cs - cd).items()})
        print("  多重集差 der-ser:", {hex(k): v for k, v in (cd - cs).items()})
        # 逐个位置对齐
        n = min(len(s), len(d))
        bad = [i for i in range(n) if s[i] != d[i]]
        print("  位置对齐 diff 数 %d / %d, 位点: %s" % (
            len(bad), n, [(i, hex(s[i]), hex(d[i])) for i in bad[:12]]))
        print()


if __name__ == "__main__":
    main()
