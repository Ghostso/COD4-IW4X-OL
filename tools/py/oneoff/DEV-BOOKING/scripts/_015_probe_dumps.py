# -*- coding: utf-8 -*-
"""015: probe candidate large dumps for the client module image."""
import struct
import sys

CANDS = [
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_low.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_zone.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_wide.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_big.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_devmap.bin",
    r"D:\BaiduNetdiskDownload\使命召唤OL\_cleanout\dump_map.bin",
]

# markers from image_best.bin (VA -> expected bytes)
MARKERS = [
    (0x7F152C, "c21400"),        # ret 0x14
    (0x7F1544, "e82fb14400"),    # call 0xc3c678
    (0x632680, "55"),            # accepted handler start
    (0x637E9A, "8b15fc132e08"),  # mov edx,[0x82e13fc]
    (0xDC69B0, "6d6d626f6f6b20616363657074656400"),  # "mmbook accepted"
    (0xE69C34, "9471dd00"),      # static listener vtable ptr
]

for path in CANDS:
    try:
        f = open(path, "rb")
    except OSError as e:
        print("%-60s OPEN FAIL %s" % (path, e))
        continue
    size = f.seek(0, 2)
    print("=" * 78)
    print("%s  size=%d (0x%X)" % (path, size, size))
    for va, want in MARKERS:
        f.seek(va)
        got = f.read(len(want) // 2).hex()
        print("   VA 0x%08X expect %-32s got %s %s"
              % (va, want, got, "MATCH" if got == want else ""))
    f.close()
