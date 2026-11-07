# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
print("=== functions referencing the 'getchallenge' path ===")
for va in pe.calls_to(0x5C05F0):
    print("   call to 0x5C05F0 from %08X" % va)
print()
print("=== who calls the state machine 0x5C05F0 (direct + indirect vtable usage) ===")
# 该函数被 vtable 调用的话，地址会作为立即数出现在数据里
for off, va in [(o, pe.off_to_va(o)) for o in pe.find_bytes(struct.pack("<I", 0x5C05F0))]:
    sec = pe.section_of(va) if va else None
    print("   imm-ref at %s [%s]" % (hex(va) if va else "-", sec.name if sec else "?"))
