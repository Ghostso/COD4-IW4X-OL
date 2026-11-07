# -*- coding: utf-8 -*-
"""在 marketplace 包里按 MD5 找那 6 张 co* 表。"""
import hashlib
import json
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
IIPS = os.path.abspath(os.path.join(ROOT, "..", "COD OL", "IIPS", "IIPSDownload"))
MAN = os.path.join(ROOT, "mkt_assets", "marketplace.client.json")
SIGS = (b"\x78\xda", b"\x78\x9c", b"\x78\x01")


def main():
    j = json.load(open(MAN, "r", encoding="utf-8"))
    want = {}
    for k, v in j.items():
        if isinstance(v, str) and len(v) == 32:
            want[v.upper()] = k
    print("目标表 %d 张" % len(want))
    names = [n for n in os.listdir(IIPS)
             if "marketplace" in n.lower() and n.endswith(".ifs")]
    names.sort()
    print("扫 %d 个 marketplace 包" % len(names))
    found = {}
    for n in names:
        p = os.path.join(IIPS, n)
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for sig in SIGS:
            start = 0
            while True:
                i = b.find(sig, start)
                if i < 0:
                    break
                start = i + 1
                try:
                    d = zlib.decompressobj(15)
                    out = d.decompress(b[i:i + 16 * 1024 * 1024]) + d.flush()
                except Exception:
                    continue
                if not out or len(out) > 12 * 1024 * 1024:
                    continue
                h = hashlib.md5(out).hexdigest().upper()
                if h in want:
                    k = want[h]
                    print("命中 %s: %s @0x%X (%d 字节)" % (k, n, i, len(out)))
                    found[k] = out
    print()
    print("命中 %d / %d" % (len(found), len(want)))
    d = os.path.join(ROOT, "mkt_assets", "co_market")
    os.makedirs(d, exist_ok=True)
    for k in found:
        with open(os.path.join(d, k), "wb") as f:
            f.write(found[k])
        print("  已写出 %s (%d 字节)" % (k, len(found[k])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
