# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== callers of 0x62F6F0 (mmbook builder) ===")
c = pe.calls_to(0x62F6F0)
print("count =", len(c))
for va in c:
    print("   %08X" % va)

print()
print("=== how is vtable slot involved? find 0x62F6F0 as data (vtable entry) ===")
for o in pe.find_bytes(struct.pack("<I", 0x62F6F0)):
    v = pe.off_to_va(o)
    print("   fileoff=%08X va=%s" % (o, hex(v) if v else "-"))

print()
print("=== strings 0xDC6724 / 0xDC672C : bytes around, to see arg count ===")
raw = pe.read(0xDC6710, 96)
print("   0xDC6710: " + raw.hex())
print()
print("=== xrefs to 0xDC6724 and 0xDC672C (any prefix) ===")
for tgt in (0xDC6724, 0xDC672C):
    print("  target %08X" % tgt)
    for pre, kind in ((b"\x68","push"),(b"\xba","mov edx"),(b"\xb8","mov eax"),
                      (b"\xb9","mov ecx"),(b"\xbb","mov ebx"),(b"\xbe","mov esi"),
                      (b"\xbf","mov edi")):
        for o in pe.find_bytes(pre + struct.pack("<I", tgt)):
            va = pe.off_to_va(o)
            if va and pe.is_exec(va):
                print("       %-8s %08X" % (kind, va))
