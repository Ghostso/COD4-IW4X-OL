# -*- coding: utf-8 -*-
"""
_dyn100_popup_tbl.py -- decode the popup registry table found next to
@PLATFORM_POPUP_CONNECTION / popup_connecting in the live image.

Layout observed around VA 0x00DE6800:
    00DE6804  00 85 E0 00   D0 35 84 00   B0 38 80 00   (3 pointers)
    00DE6810  34 85 E0 00   30 71 C7 00   B0 38 80 00   (3 pointers)
    00DE6818  FC FF FF FF   4C 00 00 00   FC FF FF FF
    00DE6824  60 00 00 00   FC FF FF FF   6C 00 00 00
    00DE6830  FC FF FF FF   58 00 00 00   "MPUI_DLC6_NAME"

That is a (int32 -4, int32 id) record stream interleaved with string names:
the -4 is a tag; the following int is a string/UI id.  This script walks the
region and prints every record with its string, so the id used by
@SF_UI_DW_LIVE_CONNECTING_FAILED (if the popup is selected by id) is visible.

Usage:
    python -X utf8 _dyn100_popup_tbl.py <image_best.bin>
"""

import os
import struct
import sys

LO = 0x00400000


def load(path):
    with open(path, "rb") as fh:
        return fh.read()


def cstr(blob, va, cap=64):
    off = va - LO
    if off < 0 or off >= len(blob):
        return None
    end = blob.find(b"\x00", off, off + cap)
    if end < 0:
        end = off + cap
    raw = blob[off:end]
    if not raw:
        return ""
    ok = all(32 <= b < 127 or b == 9 for b in raw)
    return raw.decode("ascii", "replace") if ok else None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print(__doc__)
        return 1
    blob = load(path)
    print("image %s size 0x%X" % (path, len(blob)))

    # Find every -4 sentinel followed by a plausible small id.
    print("")
    print("=" * 78)
    print("record stream: (-4, id) pairs with nearby string names")
    print("=" * 78)
    pat = struct.pack("<i", -4)
    s, n = 0, 0
    while True:
        i = blob.find(pat, s)
        if i < 0:
            break
        s = i + 1
        if i + 8 > len(blob):
            break
        idv = struct.unpack_from("<i", blob, i + 4)[0]
        if not (0 <= idv <= 100000):
            continue
        n += 1
        # look for a readable string within the next 0x40 bytes
        tail = blob[i + 8:i + 8 + 0x40]
        txt = None
        j = tail.find(b"\x00")
        if j >= 0 and j < 0x40:
            cand = tail[:j]
            if cand and all(32 <= b < 127 for b in cand):
                txt = cand.decode("ascii", "replace")
        # a leading pointer to a string is also common
        pv = struct.unpack_from("<I", blob, i + 8)[0] if i + 12 <= len(blob) else 0
        pstr = cstr(blob, pv) if LO <= pv < LO + len(blob) else None
        if txt is None and pstr is None:
            continue
        label = txt if txt is not None else ("-> " + pstr)
        print("  rec VA 0x%08X  id=%-7d 0x%X   %s" % (LO + i, idv, idv, label))
        if n > 400:
            print("  ... (truncated)")
            break
    print("total records: %d" % n)

    # Also dump the exact window with the popup names and the small-int list.
    print("")
    print("=" * 78)
    print("window 0x00DE6800 .. 0x00DE6A00 (popup names + id list)")
    print("=" * 78)
    lo, hi = 0x00DE6800, 0x00DE6A00
    for row in range(lo - LO, hi - LO, 16):
        chunk = blob[row:row + 16]
        h = " ".join("%02X" % b for b in chunk)
        a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("   %08X  %-47s  %s" % (LO + row, h, a))
    return 0


if __name__ == "__main__":
    sys.exit(main())
