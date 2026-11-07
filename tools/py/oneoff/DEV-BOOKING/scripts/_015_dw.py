# -*- coding: utf-8 -*-
"""015: dump a VA range as dwords, marking foreign pointers and listing call sites."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, cstr, MD  # noqa

lo = int(sys.argv[1], 16)
hi = int(sys.argv[2], 16)

for va in range(lo, hi, 4):
    v = struct.unpack_from("<I", DATA, va - BASE)[0]
    tag = ""
    if v and not (BASE <= v < END):
        tag = "   <-- foreign 0x%08X" % v
    s = cstr(va, 48)
    print("0x%08X  %08X%s%s" % (va, v, tag, '  "%s"' % s if s else ""))
