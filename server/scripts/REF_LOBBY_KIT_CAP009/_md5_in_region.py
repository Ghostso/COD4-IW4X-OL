# -*- coding: utf-8 -*-
"""只在 r_48110000 区里按 MD5 找那 6 张表。"""
import hashlib
import json
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_48110000_0105A000.bin")
MAN = os.path.join(ROOT, "mkt_assets", "marketplace.client.json")
SIGS = (b"\x78\xda", b"\x78\x9c", b"\x78\x01")


def main():
    j = json.load(open(MAN, "r", encoding="utf-8"))
    want = {}
    for k, v in j.items():
        if isinstance(v, str) and len(v) == 32:
            want[v.upper()] = k
    b = open(P, "rb").read()
    print("区 %d 字节, 目标 %d 张" % (len(b), len(want)))
    found = {}
    for sig in SIGS:
        start = 0
        n = 0
        while True:
            i = b.find(sig, start)
            if i < 0:
                break
            start = i + 1
            n += 1
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
                print("命中 %s @0x%X (%d 字节)" % (k, i, len(out)))
                found[k] = out
        print("  sig=%s 起点 %d 个" % (sig.hex(), n))
    print()
    print("命中 %d / %d" % (len(found), len(want)))
    d = os.path.join(ROOT, "mkt_assets", "co_market")
    os.makedirs(d, exist_ok=True)
    for k in found:
        with open(os.path.join(d, k), "wb") as f:
            f.write(found[k])
        print("  写出 %s (%d)" % (k, len(found[k])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
