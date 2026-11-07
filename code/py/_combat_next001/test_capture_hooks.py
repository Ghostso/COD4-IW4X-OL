# -*- coding: utf-8 -*-
"""NEXT-010: unit-test the capture helpers of the PATCHED COPY (no client, no network).

Proves: switch OFF = no writes; switch ON = correct meta/hex records for 21/5 and 6/14.
"""
import io
import os
import sys

COPY = sys.argv[1]
sys.path.insert(0, COPY)

import lobby_server as ls

FLAG = os.path.join(COPY, "capture-21-5.enabled")
META = os.path.join(COPY, "capture-21-5.meta")
HEX = os.path.join(COPY, "capture-21-5.hex")


def clean():
    for p in (FLAG, META, HEX):
        try:
            os.remove(p)
        except Exception:
            pass


def hashes():
    return dict((os.path.basename(p), os.path.exists(p)) for p in (META, HEX))


print("=== A) switch OFF ===")
clean()
cid = ls._cap_begin()
print("   _cap_begin ->", cid)
print("   files after OFF:", hashes())
assert cid is None, "OFF must return None"
assert not any(hashes().values()), "OFF must not create files"
print("   OK: no writes when OFF")

print("=== B) switch ON ===")
clean()
io.open(FLAG, "w").close()
cid = ls._cap_begin()
ls._cap_set(cid, ("127.0.0.1", 50001))
print("   _cap_begin/_cap_set ->", cid)
assert cid == "c0001", cid

# --- simulate the 21/5 outbound frame (306 bytes, as verified in NEXT-009) ---
frame215 = bytes(range(256)) + bytes(50)          # 306 bytes total
assert len(frame215) == 306
ls._cap_frame("S2C-PLAIN", {"service": 21, "task": 5, "seq": 47},
              frame215, 21, 5, 47, 0)

# --- simulate the 6/14 inbound plaintext frame ---
frame614 = bytes([0x0A, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
ls._cap_frame("C2S-PLAIN", {"service": 6, "task": 14, "seq": 48},
              frame614, 6, 14, 48, 0)

# --- a NON-target frame must be ignored ---
ls._cap_frame("S2C-PLAIN", {"service": 10, "task": 21, "seq": 49},
              b"publisher-bytes", 10, 21, 49, 0)

print("   files after ON:", hashes())
assert all(hashes().values()), "ON must create both files"

meta = io.open(META, encoding="utf-8").read()
hexf = io.open(HEX, encoding="utf-8").read()
print()
print("--- capture-21-5.meta ---")
for line in meta.splitlines():
    print("   " + line)
print()
print("--- capture-21-5.hex (first 120 chars) ---")
print("   " + hexf[:120].replace(chr(10), " | "))
print()

# --- assertions ---
assert "service=21" in meta and "task=5" in meta, "21/5 must be logged"
assert "service=6" in meta and "task=14" in meta, "6/14 must be logged"
assert "service=10" not in meta, "non-target must be ignored"
assert "S2C-PLAIN" in meta and "C2S-PLAIN" in meta, "directions must be recorded"
assert "len=306" in meta, "306-byte frame length must be recorded"
assert "sha256=" in meta, "sha256 must be recorded"
assert frame215.hex() in hexf, "21/5 full raw bytes must be present in hex file"
assert frame614.hex() in hexf, "6/14 full raw bytes must be present in hex file"
print("ALL CAPTURE-HOOK ASSERTIONS PASSED")
clean()
print("(cleaned up test outputs)")
