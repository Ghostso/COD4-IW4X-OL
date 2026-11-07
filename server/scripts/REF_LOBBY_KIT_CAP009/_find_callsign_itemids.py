# -*- coding: utf-8 -*-
"""在内存里找"名片物品 ID"表 —— 用已知的真实名片 item ID 做锚点。

已知: 用户买过的名片 item = 22381 / 22384 (Category=1)。
CallSignObj 的字段名(cardTitleItemID 等)也在内存里。

思路: 找这些字段名附近有没有"ID 列表", 那就是客户端读表后的结果。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")

FIELDS = [b"cardTitleItemID", b"cardIconItemID", b"cardBackgroundItemID",
          b"cardNameplateItemID", b"cardFrameItemID"]
IDS = (22381, 22384, 29892)


def main():
    hits = []
    files = 0
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        files += 1
        for f in FIELDS:
            i = b.find(f)
            if i < 0:
                continue
            # 看附近有没有已知 ID
            lo = max(0, i - 0x200)
            hi = min(len(b), i + 0x400)
            win = b[lo:hi]
            found = []
            for t in IDS:
                tp = struct.pack("<I", t)
                j = win.find(tp)
                if j >= 0:
                    found.append((t, lo + j - i))
            hits.append((fn, f.decode(), i, found))

    print("扫 %d 个区, 字段名命中 %d 处" % (files, len(hits)))
    for fn, f, i, found in hits[:40]:
        print("  %s %-24s @0x%X  邻近已知ID=%s"
              % (fn, f, i, [(t, "%+d" % d) for t, d in found]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
