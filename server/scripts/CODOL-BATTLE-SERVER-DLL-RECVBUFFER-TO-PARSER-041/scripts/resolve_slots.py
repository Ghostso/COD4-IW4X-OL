# -*- coding: utf-8 -*-
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *

# Build idata2 slot map: slot_rva -> (kind, name/ordinal)
def build_slots():
    slots = {}
    for k in range(768):
        r = 0xB02000 + 4*k
        v = rd32(r)
        if not v:
            slots[r] = (0, "NULL", "")
            continue
        if v & 0x80000000:
            slots[r] = (r, "ORDINAL", "ordinal:%d" % (v & 0xffff))
        else:
            hn = read_hintname(v)
            nm = hn[1].decode("latin1") if hn else "?"
            slots[r] = (r, "NAME", nm)
    return slots
slots = build_slots()

def resolve(va):
    return slots.get(va - IB, ("", "?", "not-a-slot"))

for a in [0x10b021d0, 0x10b02a5c, 0x10b02a40, 0x10b02a54, 0x10b02a48, 0x10b02a4c, 0x10b02a60, 0x10b02a64, 0x10b02a68, 0x10b02a6c, 0x10b02a70, 0x10b023b4, 0x10b023bc, 0x10b0221c, 0x10b02224]:
    print("0x%08X -> %s" % (a, resolve(a)))
