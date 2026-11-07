# -*- coding: utf-8 -*-
"""
_dyn100_lit.py -- find the bracket-format literal and dump the neighbourhood
of the lobby UI strings in the live image.

Usage:
    python -X utf8 _dyn100_lit.py <image_best.bin>
"""

import sys

LO = 0x00400000

PATS = [b"[%d]", b"[%u]", b"[%i]", b"[%s]", b"[100]", b"%d", b"%u",
        b"[%d]%s", b"@SF_UI_DW_LIVE_"]

WINDOWS = [
    ("SF_UI_DW_LIVE_CONNECTING_FAILED", 0x00DE0640),
    ("SF_UI_DW_LIVE_DISCONNECTED", 0x00DBD888),
    ("PLATFORM_POPUP_CONNECTION", 0x00DE68CC),
    ("popup_connecting", 0x00DE6900),
    ("Live_Frame", 0x00DE6910),
]


def main():
    path = sys.argv[1]
    with open(path, "rb") as fh:
        b = fh.read()

    print("=" * 78)
    print("format-literal occurrences")
    print("=" * 78)
    for pat in PATS:
        idx, s = [], 0
        while True:
            i = b.find(pat, s)
            if i < 0:
                break
            idx.append(i)
            s = i + 1
            if len(idx) > 60:
                break
        print("%-12s count=%d" % (pat.decode("latin1"), len(idx)))
        for o in idx[:24]:
            off = o - LO
            end = b.find(b"\x00", o, o + 40)
            ctx = b[o:end if end > 0 else o + 40]
            print("    VA 0x%08X  %r" % (LO + off, ctx))

    print("")
    print("=" * 78)
    print("string windows")
    print("=" * 78)
    for name, va in WINDOWS:
        off = va - LO
        print("")
        print("--- %s  VA 0x%08X ---" % (name, va))
        row = off - 0x30
        for r in range(row, row + 0x90, 16):
            c = b[r:r + 16]
            if not c:
                break
            asc = "".join(chr(x) if 32 <= x < 127 else "." for x in c)
            hx = " ".join("%02X" % x for x in c)
            print("  %08X  %-47s  %s" % (LO + r, hx, asc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
