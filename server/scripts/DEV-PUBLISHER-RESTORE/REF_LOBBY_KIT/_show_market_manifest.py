# -*- coding: utf-8 -*-
"""打印 mp/marketplace.json 清单, 并按 MD5 在内存里反查各表。"""
import hashlib
import json
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
MAN = os.path.join(ROOT, "mkt_assets", "marketplace.client.json")


def main():
    j = json.load(open(MAN, "r", encoding="utf-8"))
    print("== mp/marketplace.json 全文 ==")
    for k, v in j.items():
        print("  %-36s %s" % (k, v))
    print()
    want = {k: v for k, v in j.items() if k.lower().endswith(".csv")}
    print("要反查的表 %d 张" % len(want))
    found = {}
    for fn in sorted(os.listdir(MEM)):
        p = os.path.join(MEM, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for sig in (b"\x78\xda", b"\x78\x9c", b"\x78\x01"):
            start = 0
            while True:
                i = b.find(sig, start)
                if i < 0:
                    break
                start = i + 1
                try:
                    d = zlib.decompressobj(15)
                    out = d.decompress(b[i:i + 8 * 1024 * 1024]) + d.flush()
                except Exception:
                    continue
                if not out or len(out) > 6 * 1024 * 1024:
                    continue
                h = hashlib.md5(out).hexdigest().upper()
                for k, v in want.items():
                    if isinstance(v, str) and v.upper() == h:
                        print("命中 %s: %s @0x%X (%d 字节)" % (k, fn, i, len(out)))
                        found[k] = out
    print()
    print("反查命中 %d / %d 张" % (len(found), len(want)))
    if found:
        outdir = os.path.join(ROOT, "mkt_assets", "co_market")
        os.makedirs(outdir, exist_ok=True)
        for k, data in found.items():
            with open(os.path.join(outdir, k), "wb") as f:
                f.write(data)
            print("  已写出 %s (%d 字节)" % (k, len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
