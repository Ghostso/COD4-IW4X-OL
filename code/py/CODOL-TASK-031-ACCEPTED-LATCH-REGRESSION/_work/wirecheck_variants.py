# -*- coding: utf-8 -*-
"""TASK-031 offline byte-variant construction (no game, no network).
Uses the CURRENT kit crypto exactly as lobby_server.py does."""
import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT_CAP009")
import codol_crypto as cc
print("codol_crypto file:", cc.__file__)

def hx(b): return " ".join("%02x" % x for x in b)

SENDER = 0x1122334455667788
NAME   = "localhost"

variants = {}
# Variant A: current post-023 kit form  (FR_BOOKING_ACCEPTED = b"mmbook accepted\x00")
variants["A_current_post023"] = b"mmbook accepted\x00"
# Variant B: ol-mod archived form  (inner u32(15) prefix + 15-byte text, no NUL)
variants["B_olmod_archived"] = (15).to_bytes(4, "little") + b"mmbook accepted"
# Variant C: 023 pre-fix regression (inner u32(16) prefix + 16-byte text w/ NUL)
variants["C_023_prefix_regression"] = (16).to_bytes(4, "little") + b"mmbook accepted\x00"

GATE = b"mmbook accepted"
print()
print("gate (validated at 0x6326DA/0x6326DF): strncmp(arg5, %r, 15)" % GATE)
print()
for name, data in variants.items():
    body = cc.instant_push_body(SENDER, NAME, data)
    print("=" * 100)
    print("VARIANT %s" % name)
    print("  inner data len      = %d" % len(data))
    print("  inner data hex      = %s" % hx(data))
    print("  push body len       = %d" % len(body))
    print("  push body hex       = %s" % hx(body))
    first15 = data[:15]
    print("  arg5[0:15] (if arg5 == inner-data start) = %r" % first15)
    print("  strncmp==0 ?        = %s" % (first15 == GATE))
    print()
print("WIRE byte sequences exactly as lobby_server would emit them:")
for name, data in variants.items():
    body = cc.instant_push_body(SENDER, NAME, data)
    print("  %-28s %s" % (name, hx(body)))
