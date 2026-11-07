# -*- coding: utf-8 -*-
"""Confirm identity of the client by checking more doc-specified sites.
Read-only."""
IMG = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
data = open(IMG, "rb").read()
def off(va): return va - BASE
def hx(va,n):
    o=off(va); b=data[o:o+n]
    return " ".join("%02X"%x for x in b)

print("=== doc section 3 key chain: verify the addresses exist in our image ===")
print()
print("svc global 0x8269774  (doc: svc = [0x8269774])")
o = off(0x8269774)
print("   file offset 0x%X  in-range=%s" % (o, o < len(data)))
print("   bytes:", hx(0x8269774, 16))
print()
print("=== sub offsets doc relies on (these are struct field offsets, not addresses) ===")
for name, v in [("sub+0x4F4",0x4F4),("sub+0x5E8",0x5E8),("sub+0x5FC",0x5FC),
                ("sub+0x604",0x604),("sub+0x608",0x608),("sub+0x60C",0x60C)]:
    print("   %-12s offset 0x%03X" % (name, v))
print()
print("=== doc: patch4 site is the LSG nonce check at 0xBA3C1A ===")
print("   0xBA3C1A:", hx(0xBA3C1A, 8))
print("   doc says: 85 C0 75 44  -> NOP at 3rd/4th byte (0xBA3C1C)")
print("   ours     :", hx(0xBA3C1A, 4))
print()
print("=== our own project's known site 0xBA35E9 (arm fail exit) for cross-ref ===")
print("   0xBA35E0 region:", hx(0xBA35E0, 16))
print()
print("=== doc patch1 site vs our known 0xB9A78C family (TAS/auth related) ===")
print("   0xB9A78C:", hx(0xB9A78C, 32))
