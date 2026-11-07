# -*- coding: utf-8 -*-
"""解出客户端自己的商城表 mp/marketplace.json (zlib)。"""
import json
import os
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
OUT = os.path.join(ROOT, "mkt_assets")


def main():
    best = None
    for fn in sorted(os.listdir(MEM)):
        p = os.path.join(MEM, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        i = b.find(b"mp/marketplace.json")
        if i < 0:
            continue
        for sig in (b"\x78\xda", b"\x78\x9c", b"\x78\x01"):
            j = b.find(sig, i)
            if j < 0 or j - i > 0x200:
                continue
            print("命中 %s @0x%X, zlib @0x%X sig=%s" % (fn, i, j, sig.hex()))
            try:
                d = zlib.decompressobj(15)
                out = d.decompress(b[j:j + 4 * 1024 * 1024])
                out += d.flush()
            except Exception as e:
                print("  解压失败: %r" % (e,))
                continue
            print("  解出 %d 字节" % len(out))
            print("  前 200: %r" % out[:200])
            if best is None or len(out) > len(best[1]):
                best = (fn, out)
            break
    if best is None:
        print("没找到可解的 mp/marketplace.json")
        return 1
    fn, data = best
    os.makedirs(OUT, exist_ok=True)
    raw = os.path.join(OUT, "marketplace.json.raw")
    with open(raw, "wb") as f:
        f.write(data)
    print()
    print("最佳 %s, %d 字节 -> %s" % (fn, len(data), raw))
    try:
        j = json.loads(data.decode("utf-8"))
        print("★ 合法 JSON, 顶层 %s" % type(j).__name__)
        if isinstance(j, dict):
            print("  顶层键:", list(j)[:30])
            for k in j:
                v = j[k]
                if isinstance(v, list) and v:
                    print("  %s: list(%d) 首项 %s" % (k, len(v), str(v[0])[:200]))
        elif isinstance(j, list):
            print("  长度 %d, 首项 %s" % (len(j), str(j[0])[:300]))
        outj = os.path.join(OUT, "marketplace.client.json")
        with open(outj, "w", encoding="utf-8") as f:
            json.dump(j, f, ensure_ascii=False, separators=(",", ":"))
        print("  已写出 %s" % outj)
    except Exception as e:
        print("  不是 JSON(%r), 保留 .raw" % (e,))
    return 0


if __name__ == "__main__":
    sys.exit(main())
