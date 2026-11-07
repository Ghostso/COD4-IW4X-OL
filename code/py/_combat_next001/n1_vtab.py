# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== vtable/data references to the battle-booking functions ===")
for name, a in (("0x62F840", 0x62F840), ("0x62F6F0", 0x62F6F0), ("0x632680", 0x632680),
                ("0x632070", 0x632070), ("0x631E90", 0x631E90)):
    hits = []
    for o in pe.find_bytes(struct.pack("<I", a)):
        v = pe.off_to_va(o)
        sec = pe.section_of(v) if v else None
        hits.append((o, v, sec.name if sec else "?"))
    print("  %-9s refs=%d" % (name, len(hits)))
    for o, v, sn in hits[:6]:
        print("        fileoff=%08X va=%s sect=%s" % (o, hex(v) if v else "-", sn))
print()
print("=== the two arrays: read index math in accepted handler (0x6326EF) ===")
for l in pe.dis(0x6326EF, 10):
    print(l)
print()
print("=== what is at +0x75D8 and +0x7470? check init function 0x62CD2F area ===")
for l in pe.dis(0x62CD2F, 40):
    print(l)
