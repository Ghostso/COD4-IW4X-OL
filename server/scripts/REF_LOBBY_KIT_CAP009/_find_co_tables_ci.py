# -*- coding: utf-8 -*-
"""大小写不敏感地找那 5 张 co* 表, 并尝试解其后的 zlib。"""
import hashlib
import os
import re
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
OUT = os.path.join(ROOT, "mkt_assets", "co_market")
PAT = re.compile(rb"[a-z0-9_/]{0,20}(?:co)?marketplace[a-z0-9_]{0,20}\.csv", re.I)


def try_zlib(b, start):
    for sig in (b"\x78\xda", b"\x78\x9c", b"\x78\x01"):
        j = b.find(sig, start)
        if 0 <= j - start < 0x400:
            try:
                d = zlib.decompressobj(15)
                out = d.decompress(b[j:j + 8 * 1024 * 1024]) + d.flush()
                if out:
                    return j, out
            except Exception:
                pass
    return None, None


def main():
    os.makedirs(OUT, exist_ok=True)
    hits = {}
    for fn in sorted(os.listdir(MEM)):
        p = os.path.join(MEM, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for m in PAT.finditer(b):
            name = m.group(0).decode("latin1")
            key = name.lower().split("/")[-1]
            j, data = try_zlib(b, m.end())
            if data is None:
                continue
            if key not in hits or len(data) > len(hits[key][1]):
                hits[key] = (name, data, fn, m.start(), j)
    print("找到 %d 张表" % len(hits))
    for key in sorted(hits):
        name, data, fn, i, j = hits[key]
        out = os.path.join(OUT, key)
        with open(out, "wb") as f:
            f.write(data)
        print()
        print("== %s ==" % name)
        print("   %s @0x%X zlib@0x%X -> %d 字节" % (fn, i, j, len(data)))
        print("   md5=%s" % hashlib.md5(data).hexdigest().upper())
        print("   前 300: %s" % data[:300].decode("utf-8", "replace").replace("\n", " | "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
