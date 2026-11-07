# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

print("=== data refs (vtable slots) for the slot fillers ===")
for name, a in (("0x637590", 0x637590), ("0x637720", 0x637720),
                ("0x6376F0", 0x6376F0), ("0x62CD30", 0x62CD30)):
    hits = []
    for o in pe.find_bytes(struct.pack("<I", a)):
        v = pe.off_to_va(o)
        hits.append((o, v))
    print("  %-9s data-refs=%d" % (name, len(hits)))
    for o, v in hits[:8]:
        print("      fileoff=%08X va=%s" % (o, hex(v) if v else "-"))
    print()

print("=== vtable containing 0x637590 (0xDC6556-0xDC6560 neighbourhood) ===")
# 0xdc6556 was a data-ref for 0x63735F; dump the vtable window
print("  0xDC6540..0xDC65A0:")
raw = pe.read(0xDC6540, 0x60)
for i in range(0, 0x60, 4):
    val = struct.unpack_from("<I", raw, i)[0]
    print("    %08X: %08X" % (0xDC6540 + i, val))
