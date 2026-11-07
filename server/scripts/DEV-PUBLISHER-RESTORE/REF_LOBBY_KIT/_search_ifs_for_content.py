# -*- coding: utf-8 -*-
"""拿已解密的商城表内容串去所有 .ifs 里搜。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IIPS = os.path.abspath(os.path.join(ROOT, "..", "COD OL", "IIPS", "IIPSDownload"))
NEEDLES = [b"UI_MARKET_COMPONY_LEVISTHAN_NAME", b"coMarketplace",
           b"coMarketplaceProductItems", b"MarketplaceProductItems",
           b"MarketplaceSKUs", b"unlockFlags", b"marketplace.json"]


def main():
    names = [n for n in os.listdir(IIPS) if n.lower().endswith(".ifs")]
    names.sort()
    print("扫 %d 个 .ifs" % len(names))
    hits = {}
    for n in names:
        p = os.path.join(IIPS, n)
        try:
            if os.path.getsize(p) > 900 * 1024 * 1024:
                continue
            b = open(p, "rb").read()
        except Exception:
            continue
        for nd in NEEDLES:
            if nd in b:
                hits.setdefault(nd.decode(), []).append(n)
    print()
    for nd in NEEDLES:
        k = nd.decode()
        lst = hits.get(k, [])
        print("%-34s %d 个包" % (k, len(lst)))
        for n in lst[:6]:
            print("     %s" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
