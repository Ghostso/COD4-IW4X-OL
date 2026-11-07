# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data

print("=== who invokes 0x6376F0 via 0x7FAA20 (activator)? ===")
# 0x7FAA20 是激活器；找它附近的调用点
for o in pe.find_bytes(b"\xe8"):
    if o + 5 > len(d): continue
    rel = struct.unpack_from("<i", d, o+1)[0]
    va = pe.off_to_va(o)
    if not va or not pe.is_exec(va): continue
    t = va + 5 + rel
    if t == 0x7FAA20:
        print("   call 0x7FAA20 from %08X" % va)

print()
print("=== 0x7F4700 .. 0x7F4490 : what message dispatch reaches 0x7F4477? ===")
# 向上找 0x7F4477 所在函数
for back in range(1, 0x900):
    x = 0x7F4477 - back
    b = pe.read(x, 2)
    if b and b[0] == 0xCC and b[1] == 0xCC:
        print("   function start ~%08X" % (x+1)); break

print()
print("=== strings referenced in that function region (0x7F4400..0x7F4480) ===")
seg = pe.read(0x7F43E0, 0xC0)
seen=set()
for k in range(len(seg)-5):
    if seg[k] in (0x68, 0xBA, 0xB8, 0xB9, 0xBB, 0xBE, 0xBF):
        v = struct.unpack_from("<I", seg, k+1)[0]
        if 0xD00000 <= v <= 0xE60000 and v not in seen:
            seen.add(v)
            raw = pe.read(v, 60)
            z = raw.find(b"\0")
            s = raw[:z if z>=0 else 60].decode("latin1", "replace")
            print("   %08X %r" % (v, s))
