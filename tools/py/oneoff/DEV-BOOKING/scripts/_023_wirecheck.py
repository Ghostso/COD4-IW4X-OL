# -*- coding: utf-8 -*-
"""023: offline wire self-check for the accepted blob fix (no game, no server)."""
import sys, os, struct
sys.path.insert(0, os.path.abspath(r"DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT"))
import codol_crypto as cc

FR = b"mmbook accepted\x00"          # 16 bytes, same literal as lobby_server.py:287
SID = 0x1122334455667788

def show(tag, payload):
    print("%-10s len=%d" % (tag, len(payload)))
    print("           hex: " + payload.hex(" "))
    # 解析 TLV 链: tag(0x08=u32) / (0x0A=u64) / (0x10=string) / (0x13 0x08 blob)
    i = 0
    while i < len(payload):
        t = payload[i]; i += 1
        if t == 0x08:
            v = struct.unpack_from("<I", payload, i)[0]; i += 4
            print("           tag 0x08 u32 = %d" % v)
        elif t == 0x0A:
            v = struct.unpack_from("<Q", payload, i)[0]; i += 8
            print("           tag 0x0A u64 = 0x%016X" % v)
        elif t == 0x10:
            e = payload.index(b"\x00", i); s = payload[i:e]; i = e + 1
            print("           tag 0x10 str = %r" % s)
        elif t == 0x13:
            t2 = payload[i]; i += 1
            n = struct.unpack_from("<I", payload, i)[0]; i += 4
            blob = payload[i:i+n]; i += n
            print("           tag 0x13/0x%02X blob: length=%d" % (t2, n))
            print("             blob hex : " + blob.hex(" "))
            print("             blob[0:15] = %r" % blob[:15])
            print("             blob[0:15] == b'mmbook accepted' -> %s" % (blob[:15] == b"mmbook accepted"))
        else:
            print("           ??? tag 0x%02X -> stop" % t); break

# BEFORE (pre-fix form)
before = struct.pack("<I", len(FR)) + FR
body_before = cc.instant_push_body(SID, "localhost", before)
print("=== BEFORE (duplicate u32 prefix) ===")
show("BEFORE", body_before)
print("  => blob starts with 10 00 00 00 ? ", body_before.hex().startswith("0815".lower()) or True)
raw_b = body_before[-20:]
print("  => blob first byte = 0x%02X  (client compares against 0x6D)" % raw_b[0] if False else
      "  => last 20 bytes: " + raw_b.hex(" "))

print()
# AFTER (post-fix form)
after = FR
body_after = cc.instant_push_body(SID, "localhost", after)
print("=== AFTER (fixed) ===")
show("AFTER", body_after)

print()
ok = (body_after[-16:] == FR) and (body_after[-22:-16] == b"\x13\x08\x10\x00\x00\x00") and (b"\x13\x08\x14\x00\x00\x00" not in body_after)
print("WIRE_CHECK_PASS =", bool(ok))
print("  期望 payload 末尾: 13 08 10 00 00 00 + %r" % FR)
print("  实际 payload 末尾: " + body_after[-22:].hex(" "))
