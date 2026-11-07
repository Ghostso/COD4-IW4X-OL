# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def cstr(va, maxn=140):
    b = pe.read(va, maxn)
    if not b: return None
    z = b.find(b"\0")
    return b[:z if z >= 0 else maxn].decode("latin1", "replace")

print("=== 0x47035F .. 0x470470 (entry of the battle-start function) ===")
for l in pe.dis(0x47035F, 90):
    print(l)
print()
print("=== callers of 0x47035F ===")
for va in pe.calls_to(0x47035F):
    print("   %08X" % va)
print()
print("=== strings referenced inside 0x47035F..0x470600 ===")
seg = pe.read(0x47035F, 0x2A0)
seen = set()
for k in range(len(seg) - 5):
    if seg[k] in (0x68, 0xBA, 0xB8, 0xB9, 0xBB, 0xBE, 0xBF):
        v = struct.unpack_from("<I", seg, k + 1)[0]
        if 0xD00000 <= v <= 0xE60000 and v not in seen:
            seen.add(v)
            s = cstr(v)
            if s:
                print("   %08X %r" % (v, s[:60]))
