# -*- coding: utf-8 -*-
"""019: dump the 21/5 mission session object fields (tag/value) to identify #7 / #28."""
import os, struct, sys
KIT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "DEV-PUBLISHER-RESTORE", "REF_LOBBY_KIT")
sys.path.insert(0, KIT)
import codol_crypto as cc

buf = cc.build_mission_session_object(playlist=10)
print("object length = %d bytes" % len(buf))
print("hex[:64] =", buf[:64].hex())

TAGLEN = {0x01: 1, 0x03: 1, 0x06: 2, 0x07: 4, 0x08: 4, 0x09: 8, 0x0A: 8}
i = 0
n = 0
while i < len(buf) and n < 12:
    t = buf[i]
    n += 1
    if t in TAGLEN:
        ln = TAGLEN[t]
        v = buf[i+1:i+1+ln]
        val = int.from_bytes(v, "little")
        print("  #%-2d off=0x%03X tag=0x%02X len=%d value=%d (0x%X) bytes=%s"
              % (n, i, t, ln, val, val, v.hex()))
        i += 1 + ln
    elif t == 0x10:
        e = buf.index(b"\x00", i+1)
        print("  #%-2d off=0x%03X tag=0x10 string=%r" % (n, i, buf[i+1:e].decode("ascii", "replace")))
        i = e + 1
    elif t == 0x13:
        # blob = 13 08 <u32 len> data
        ln = struct.unpack_from("<I", buf, i+2)[0]
        print("  #%-2d off=0x%03X tag=0x13 blob len=%d data=%s" % (n, i, ln, buf[i+6:i+6+ln].hex()))
        i += 6 + ln
    else:
        print("  #%-2d off=0x%03X tag=0x%02X (skip rest)" % (n, i, t))
        break

# locate all tag-0x0A u64 occurrences and their byte offsets
print("=== all tag-0x0A u64 fields ===")
for j in range(len(buf)-9):
    if buf[j] == 0x0A:
        v = struct.unpack_from("<Q", buf, j+1)[0]
        print("  off=0x%03X u64=%d (0x%X) bytes=%s" % (j, v, v, buf[j:j+9].hex()))
