# -*- coding: utf-8 -*-
"""015: dword + ascii dump of a VA range."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa

lo = int(sys.argv[1], 16)
hi = int(sys.argv[2], 16)
for va in range(lo, hi, 16):
    off = va - BASE
    chunk = DATA[off:off + 16]
    dw = struct.unpack_from("<4I", chunk, 0)
    asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
    print("0x%08X  %s  |%s|" % (va, " ".join("%08X" % x for x in dw), asc))
