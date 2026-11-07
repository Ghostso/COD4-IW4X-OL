# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

FUN = 0x470360
print("=== immediate references to 0x470360 anywhere in the image ===")
for o in pe.find_bytes(struct.pack("<I", FUN)):
    va = pe.off_to_va(o)
    sec = pe.section_of(va) if va else None
    execflag = pe.is_exec(va) if va else False
    print("   fileoff=%08X va=%s sect=%s exec=%s" % (o, hex(va) if va else "-",
          sec.name if sec else "-", execflag))
print()
print("=== also check 0x47035F (entry with padding) ===")
for o in pe.find_bytes(struct.pack("<I", 0x47035F)):
    va = pe.off_to_va(o)
    print("   fileoff=%08X va=%s" % (o, hex(va) if va else "-"))
