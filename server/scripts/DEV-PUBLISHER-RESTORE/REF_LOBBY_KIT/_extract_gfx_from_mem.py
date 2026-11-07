# -*- coding: utf-8 -*-
"""从内存转储里提取 Scaleform SWF(FWS/CWS/ZWS), 找出含指定类的影片。

背景: 客户端 UI 是 Scaleform; MarketScrollGrid.as / MatchMakingStripView.as
等 .as 类名在内存里能找到, 但要看它们"读什么数据"需要 AS3 字节码。
SWF 头: FWS(未压缩) / CWS(zlib) / ZWS(LZMA)。
ZWS: 8B 头 + 5B LZMA props + 4B 未压缩长度 + LZMA 数据。
"""
import lzma
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
WANT = [b"MarketScrollGrid", b"MatchMakingStripView", b"MarketplaceView",
        b"SupplyDropView", b"OnboardingChallengesChecklistListItem",
        b"MOTDNotificationsPopup"]


def swf_uncompress(sig, raw):
    if sig == b"FWS":
        return raw
    if sig == b"CWS":
        return raw[:8] + zlib.decompress(raw[8:])
    # ZWS
    props = raw[8:13]
    if len(props) < 5:
        raise ValueError("short zws")
    lc = props[0] % 9
    lp = (props[0] // 9) % 5
    pb = props[0] // 45
    dsize = struct.unpack_from("<I", props, 1)[0]
    unc = struct.unpack_from("<I", raw, 13)[0]
    dec = lzma.LZMADecompressor(
        format=lzma.FORMAT_RAW,
        filters=[{"id": lzma.FILTER_LZMA1, "lc": lc, "lp": lp, "pb": pb,
                  "dict_size": max(4096, dsize)}])
    body = dec.decompress(raw[17:17 + unc])
    return raw[:8] + body


def main():
    hits = 0
    for fn in sorted(os.listdir(MEM)):
        p = os.path.join(MEM, fn)
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for sig in (b"FWS", b"CWS", b"ZWS"):
            start = 0
            while True:
                i = b.find(sig, start)
                if i < 0:
                    break
                start = i + 1
                if i + 8 > len(b):
                    break
                ver = b[i + 3]
                ln = struct.unpack_from("<I", b, i + 4)[0]
                if not (512 < ln <= 60 * 1024 * 1024):
                    continue
                if i + ln > len(b):
                    continue
                raw = b[i:i + ln]
                try:
                    data = swf_uncompress(sig, raw)
                except Exception:
                    continue
                found = [w.decode() for w in WANT if w in data]
                if not found:
                    continue
                hits += 1
                print("%-30s %s @0x%X ver=%d wire=%d plain=%d  %s"
                      % (fn, sig.decode(), i, ver, ln, len(data), found))
                for w in found:
                    out = os.path.join(ROOT, "_gfx_%s_%08X.swf" % (w, i))
                    with open(out, "wb") as f:
                        f.write(data)
                    print("     ->", os.path.basename(out))
    print("命中影片 %d 个" % hits)
    return 0


if __name__ == "__main__":
    sys.exit(main())
