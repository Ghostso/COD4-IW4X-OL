# -*- coding: utf-8 -*-
"""
_dyn100_ptr.py -- find 4-byte pointers to selected lobby strings and decode
the surrounding table.  This is the data-side companion to the immediate
operand scan.

Usage:
    python -X utf8 _dyn100_ptr.py <image_best.bin>
"""

import struct
import sys

LO = 0x00400000
TARGETS = {
    "SF_UI_DW_LIVE_CONNECTING_FAILED": 0x00DE0640,
    "SF_UI_DW_LIVE_DISCONNECTED": 0x00DBD888,
    "SF_UI_DW_LIVE_CERT_FAILED": 0x00DE09F0,
    "PLATFORM_POPUP_CONNECTION": 0x00DE68CC,
    "popup_connecting": 0x00DE6900,
    "Live_Frame": 0x00DE6910,
    "during_startup": 0x00DE68E8,
}


def cstr(blob, va, cap=64):
    off = va - LO
    if off < 0 or off >= len(blob):
        return ""
    end = blob.find(b"\x00", off, off + cap)
    if end < 0:
        end = off + cap
    raw = blob[off:end]
    return raw.decode("ascii", "replace") if raw else ""


def main():
    path = sys.argv[1]
    with open(path, "rb") as fh:
        b = fh.read()
    print("image size 0x%X" % len(b))
    for name, va in TARGETS.items():
        pat = struct.pack("<I", va)
        hits = []
        s = 0
        while True:
            i = b.find(pat, s)
            if i < 0:
                break
            hits.append(i)
            s = i + 1
        print("")
        print("=" * 78)
        print("%s  VA 0x%08X  pointer hits=%d" % (name, va, len(hits)))
        for off in hits[:80]:
            before = b[max(0, off - 32):off]
            after = b[off + 4:off + 36]
            vals = [struct.unpack_from("<I", b, off + 4 * k)[0]
                    for k in range(-4, 9)
                    if 0 <= off + 4 * k <= len(b) - 4]
            print("  slot VA 0x%08X" % (LO + off))
            print("    before:", before.hex())
            print("    after :", after.hex())
            print("    dwords:", " ".join("0x%08X" % v for v in vals))
            # if this is a table of pointers into .rdata, decode following
            # entries whose values point to printable strings
            for k in range(0, 8):
                p = struct.unpack_from("<I", b, off + 4 * k)[0]
                if LO <= p < LO + len(b):
                    s2 = cstr(b, p)
                    if s2 and any(32 <= ord(ch) < 127 for ch in s2):
                        print("      +0x%02X -> 0x%08X  %s"
                              % (4 * k, p, s2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
