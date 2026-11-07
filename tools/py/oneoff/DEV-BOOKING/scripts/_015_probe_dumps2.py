# -*- coding: utf-8 -*-
"""015: try 12-byte-header large dumps for module content at VA 0x0E60CAF8."""
import struct
import sys

CANDS = [
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_low.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_zone.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_wide.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_devmap.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_map.bin",
]
MARKERS = [
    (0x7F152C, "c21400"),
    (0x632680, "55"),
    (0xDC69B0, "6d6d626f6f6b20616363657074656400"),
    (0xE69C34, "9471dd00"),
    (0xE60CAF8, None),
]

for path in CANDS:
    try:
        f = open(path, "rb")
    except OSError as e:
        print("%s OPEN FAIL %s" % (path, e))
        continue
    size = f.seek(0, 2)
    f.seek(0)
    head = f.read(16)
    print("=" * 78)
    print("%s size=0x%X head=%s" % (path, size, head.hex()))
    for hdr in (0, 12):
        ok = 0
        for va, want in MARKERS[:4]:
            f.seek(hdr + va)
            got = f.read(len(want) // 2).hex()
            if got == want:
                ok += 1
        if ok:
            print("   HDR=%d  markers matched %d/4" % (hdr, ok))
            f.seek(hdr + 0xE60CAF8)
            b = f.read(16)
            print("      VA 0x0E60CAF8 -> %s  -> %s"
                  % (b.hex(), " ".join("%08X" % x for x in struct.unpack("<4I", b))))
    f.close()
