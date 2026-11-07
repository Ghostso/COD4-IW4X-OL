# -*- coding: utf-8 -*-
"""找"拥有判定"的 API 名和调用点 —— 名片能不能用就看这里。

已知接口(交接文档): AS_IsMarketplaceItemOwned / AS_IsPermanentOwnedProduct /
                   AS_IsItemEquipped
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
NEEDLES = [b"AS_IsMarketplaceItemOwned", b"AS_IsPermanentOwnedProduct",
           b"AS_IsItemEquipped", b"AS_GetItemIDsFromProduct",
           b"AS_GetItemInfoBySku", b"IsMarketplaceItemOwned",
           b"IsPermanentOwnedProduct", b"isOwned", b"hasItem",
           b"itemOwned"]


def main():
    hits = {}
    for fn in sorted(os.listdir(MEM)):
        p = os.path.join(MEM, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for nd in NEEDLES:
            if nd in b:
                i = b.find(nd)
                hits.setdefault(nd.decode(), []).append((fn, i))
    for k in sorted(hits):
        print("== %s: %d 个区 ==" % (k, len(hits[k])))
        for fn, i in hits[k][:4]:
            b = open(os.path.join(MEM, fn), "rb").read()
            lo = max(0, i - 100)
            hi = min(len(b), i + 160)
            strs = re.findall(rb"[ -~]{3,80}", b[lo:hi])
            print("   %s @0x%X" % (fn, i))
            print("      %s" % b" | ".join(strs).decode("latin1")[:200])
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
