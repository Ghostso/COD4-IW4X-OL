#!/usr/bin/env python3
"""完整转储 0x73A700-0x73AC00 的 u32 流, 识别 {ptr,val} 对与数字串。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()
DELTA = 0x714000  # off->VA

def rd_str(va):
    o = va - DELTA
    if not (0 <= o < len(data)): return None
    e = data.find(b"\x00", o)
    if e < 0 or e - o > 80: return None
    try:
        s = data[o:e].decode("ascii")
        return s if all(32 <= c < 127 for c in data[o:e]) else None
    except Exception:
        return None

lo, hi = 0x73A700, 0x73AC00
print("=== 0x%X-0x%X ===" % (lo, hi))
p = lo
while p + 4 <= hi:
    v = struct.unpack_from("<I", data, p)[0]
    s = rd_str(v)
    extra = ""
    if s: extra = " -> STR %r" % s
    elif 0 < v < 0x10000: extra = "  (=%d)" % v
    print("  0x%06X: 0x%08X%s" % (p, v, extra))
    p += 4
