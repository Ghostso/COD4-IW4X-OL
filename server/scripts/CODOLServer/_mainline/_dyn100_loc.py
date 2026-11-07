# -*- coding: utf-8 -*-
"""
_dyn100_loc.py -- map UI keys to localization ids in the live image.

The popup panels are rendered as "[<id>] <text>" where <id> is the
localization id of the key.  This script looks for the (id, key) association
tables in .rdata so the id shown as "[100]" can be tied to a key.

Usage:
    python -X utf8 _dyn100_loc.py <image_best.bin>
"""

import struct
import sys

LO = 0x00400000

KEYS = [
    "@SF_UI_DW_LIVE_CONNECTING_FAILED",
    "@SF_UI_DW_LIVE_DISCONNECTED",
    "@SF_UI_DW_LIVE_CERT_FAILED",
    "@PLATFORM_POPUP_CONNECTION",
]


def main():
    path = sys.argv[1]
    with open(path, "rb") as fh:
        b = fh.read()

    for key in KEYS:
        kb = key.encode()
        pos = b.find(kb)
        if pos < 0:
            print("%s NOT FOUND" % key)
            continue
        kva = LO + pos
        print("")
        print("=" * 78)
        print("%s  VA 0x%08X" % (key, kva))
        print("=" * 78)
        # search for any 4-byte pointer to kva
        pat = struct.pack("<I", kva)
        s, refs = 0, []
        while True:
            i = b.find(pat, s)
            if i < 0:
                break
            refs.append(i)
            s = i + 1
        print("  pointer refs: %d" % len(refs))
        for r in refs[:20]:
            # print surrounding 32 bytes as dwords (possible id, ptr pairs)
            base = r - 24
            dwords = []
            for k in range(0, 64, 4):
                if base + k + 4 <= len(b):
                    dwords.append(struct.unpack_from("<I", b, base + k)[0])
            print("    ref VA 0x%08X" % (LO + r))
            print("      dwords: " + " ".join("%08X" % d for d in dwords))
        # also search for the key with a preceding small int id within 8 bytes
        for d in range(4, 40, 4):
            if pos - d >= 0:
                v = struct.unpack_from("<I", b, pos - d)[0]
                if v <= 20000:
                    print("    id-like dword %d at key-0x%X" % (v, d))
        for d in range(4, 40, 4):
            if pos + len(kb) + d + 4 <= len(b):
                v = struct.unpack_from("<I", b, pos + len(kb) + d)[0]
                if v <= 20000:
                    print("    id-like dword %d at key+len+0x%X" % (v, d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
