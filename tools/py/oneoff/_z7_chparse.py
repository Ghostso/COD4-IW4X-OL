# -*- coding: utf-8 -*-
"""Send the EXACT captured ClientHello (with compression+ext) and record the
server's raw reply. We must send a complete record: our capture may be only
the first record and the hello continues."""
import socket, ssl, threading, time

RAW = bytes.fromhex(
 "16 03 01 00 41 01 00 00 3D 03 01 6A C0 8E E1 19 5C 9F 64 76 2F 1E 55 DF C5 6D F2 6E "
 "B9 33 D0 B7 CD 8A F2 B7 D1 39 44 F4 B7 C0 3B 00 00 16 00 39 00 38 00 35 00 33 00 32 "
 "00 2F 00 16 00 13 00 0A")

# parse it
print("record len =", int.from_bytes(RAW[3:5], "big"))
print("hs len     =", int.from_bytes(RAW[6:9], "big"))
print("body starts at 9, ends at", 9 + int.from_bytes(RAW[6:9], "big"))
body_end = 9 + int.from_bytes(RAW[6:9], "big")
print("total needed:", body_end, "have:", len(RAW))
print("tail bytes:", " ".join("%02X"%x for x in RAW[body_end:]) or "(none)")
print()
print("=> ClientHello body is COMPLETE at", body_end, "bytes")
print("   missing after suites: compression_methods(1) + extensions(2)=3 bytes")
print("   but body says len", int.from_bytes(RAW[6:9],"big"), "and suites end at", body_end)
