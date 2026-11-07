# -*- coding: utf-8 -*-
"""Compare the 4 patch sites from CODOL_LOBBY_WORKING_20261002.md
against our static image.  Read-only.  Base = 0x400000."""
import io, struct

IMG = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
data = open(IMG, "rb").read()
print("image: %s  %d bytes" % (IMG, len(data)))
print()

def off(va):
    return va - BASE

def hexs(b):
    return " ".join("%02X" % x for x in b)

def show(label, va, n):
    o = off(va)
    if o < 0 or o + n > len(data):
        print("  %-28s VA=0x%08X  OUT OF RANGE" % (label, va))
        return None
    b = data[o:o+n]
    print("  %-28s VA=0x%08X  off=0x%X  %s" % (label, va, o, hexs(b)))
    return b

print("=== doc section 4: the four compat patches ===")
print("[1] 0x00B9A78C-16 .. +40  expect pattern containing  84 C0 (74|75) B2 B0 01")
show("0xB9A77C window(40B)", 0xB9A77C, 40)
print()
print("[2] 0x00B9A7B0 .. +64   expect pattern containing  84 C0 (75|EB) 2A E8")
show("0xB9A7B0 window(64B)", 0xB9A7B0, 64)
print()
print("[3] same region: call + 8D 8D 38 FD FF FF C7 85 68 FD FF FF")
show("0xB9A7C0 window(32B)", 0xB9A7C0, 32)
print()
print("[4] 0x00BA3C1A  expect 85 C0 75 44   (NOP at 0xBA3C1C)")
show("0xBA3C1A window(16B)", 0xBA3C1A, 16)
print()

print("=== the exact single bytes the doc says it patched ===")
for label, va, want in [
    ("0x00B9A78E  expect 74 or 75", 0xB9A78E, None),
    ("0x00B9A7C5  expect 75 or 90", 0xB9A7C5, None),
    ("0x00B9A7C7  expect E8",       0xB9A7C7, None),
    ("0x00BA3C1C  expect 75",       0xBA3C1C, None),
]:
    o = off(va)
    b = data[o:o+1]
    print("  %-34s byte = %s" % (label, hexs(b) if b else "OOR"))
