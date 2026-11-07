# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== refs to the message vtable 0xD5A64C ===")
for o in pe.find_bytes(struct.pack("<I", 0xD5A64C)):
    v = pe.off_to_va(o)
    print("   fileoff=%08X va=%s" % (o, hex(v) if v else "-"))

print()
print("=== vtable at 0xD5A64C (message object methods) ===")
for i in range(0, 16):
    va = 0xD5A64C + i*4
    v = struct.unpack("<I", pe.read(va, 4))[0]
    print("   [%2d] +0x%02X  %08X" % (i, i*4, v))

print()
print("=== scalar-deleting-dtor pattern: refs to 0xD5A64C in .data tables ===")
for o in pe.find_bytes(struct.pack("<I", 0xD5A64C)):
    b = pe.read(pe.off_to_va(o) - 8, 24)
    print("   ctx@%s: %s" % (hex(pe.off_to_va(o)), b.hex() if b else "-"))
