# -*- coding: utf-8 -*-
"""015: resolve MSVC RTTI COL -> class name."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, cstr  # noqa


def col_name(col):
    off = col - BASE
    if off < 0 or off + 0x14 > len(DATA):
        return None
    sig, ofs, cd, ptd, pcd = struct.unpack_from("<5I", DATA, off)
    name = cstr(ptd, 200)
    base = None
    # class descriptor: {signature, attributes, numBaseClasses, pBaseClassArray}
    if BASE <= pcd < END:
        o2 = pcd - BASE
        if o2 + 0x10 <= len(DATA):
            sig2, attr, nbase, pbasearr = struct.unpack_from("<4I", DATA, o2)
            if BASE <= pbasearr < END:
                o3 = pbasearr - BASE
                if o3 + 4 <= len(DATA):
                    first = struct.unpack_from("<I", DATA, o3)[0]
                    if BASE <= first < END:
                        base = cstr(first + 8, 200)
    return name, base


for a in sys.argv[1:]:
    col = int(a, 16)
    r = col_name(col)
    if r is None:
        print("0x%08X  <unreadable>" % col)
    else:
        print("0x%08X  name=%s   base=%s" % (col, r[0], r[1]))
