#!/usr/bin/env python3
"""任何指向串区 0x6CC900..0x6CD200 的 u32 (VA 或 RVA), 打印位置与上下文。"""
import struct

PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
data = open(PATH, "rb").read()
BASE = 0x400000
LO, HI = 0x6CC900, 0x6CD200

def scan(mode):
    res = []
    for p in range(0, len(data) - 4, 4):
        v = struct.unpack_from("<I", data, p)[0]
        if mode == "va":
            if BASE + LO <= v <= BASE + HI:
                res.append((p, v, v - BASE))
        else:
            if LO <= v <= HI:
                res.append((p, v, v))
    return res

for mode in ("va", "rva"):
    r = scan(mode)
    print("=== mode=%s  命中 %d ===" % (mode, len(r)))
    for p, v, off in r[:80]:
        # 目标串
        e = data.find(b"\x00", off)
        s = data[off:e].decode("latin1") if 0 < e - off < 48 else ""
        print("  @0x%06X val=0x%08X -> 0x%X %r" % (p, v, off, s))
