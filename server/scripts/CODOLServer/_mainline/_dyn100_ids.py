# -*- coding: utf-8 -*-
"""
_dyn100_ids.py -- decode the string-id table around 0x00DE6914 and the
popup registry ids, to see whether the "[100]" label is a UI id.

Usage:
    python -X utf8 _dyn100_ids.py <image_best.bin>
"""

import struct
import sys

LO = 0x00400000


def main():
    path = sys.argv[1]
    with open(path, "rb") as fh:
        b = fh.read()

    # Walk VA 0x00DE68CC .. 0x00DE6A60 as 4-byte slots, print printable
    # strings and their slots.
    print("slots 0x00DE68CC .. 0x00DE6A60:")
    va = 0x00DE68CC
    while va < 0x00DE6A60:
        off = va - LO
        c = b[off:off + 16]
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in c)
        dw = struct.unpack_from("<I", b, off)[0]
        d2 = struct.unpack_from("<I", b, off + 4)[0]
        print("  %08X  %-47s  %s   dw=0x%08X w=%d" %
              (va, " ".join("%02X" % x for x in c), asc, dw,
               struct.unpack_from("<H", b, off)[0]))
        va += 16

    # Enumerate the id strings 1750..1770 etc.  They appear as ASCII text.
    print("")
    print("scan for ASCII decimal ids 1700..1800 and 3200..3400 in .rdata:")
    import re
    for m in re.finditer(rb"(?<![0-9])(1[0-9]{3}|3[0-9]{3})(?![0-9])", b):
        val = int(m.group(1))
        if 1700 <= val <= 1800 or 3200 <= val <= 3400:
            print("  VA 0x%08X  id=%d  ctx=%r"
                  % (LO + m.start(), val, b[m.start() - 8:m.start() + 24]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
