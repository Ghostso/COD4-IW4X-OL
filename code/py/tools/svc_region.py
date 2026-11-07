#!/usr/bin/env python3
"""转储 0x6CCA00-0x6CD200 区域, 按 NUL 分割出串表。"""
PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()

lo, hi = 0x6CC900, 0x6CD200
chunk = data[lo:hi]
# 按 NUL 分
parts = chunk.split(b"\x00")
off = lo
print("=== 0x%X-0x%X 按 NUL 分割 ===" % (lo, hi))
for p in parts:
    if p:
        try:
            s = p.decode("ascii")
            ok = all(32 <= c < 127 for c in p)
        except Exception:
            s = p.hex()
            ok = False
        print("  0x%06X len=%3d %s %r" % (off, len(p), "TXT" if ok else "BIN", s if ok else p[:24].hex()))
    off += len(p) + 1
