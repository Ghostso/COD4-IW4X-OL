# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def cstr(va, maxn=100):
    b = pe.read(va, maxn)
    if not b: return None
    z = b.find(b"\0")
    return b[:z if z >= 0 else maxn].decode("latin1", "replace")

def fs(va):
    for back in range(1, 0x1200):
        x = va - back
        b = pe.read(x, 2)
        if b and b[0] == 0xCC and b[1] == 0xCC:
            return x + 1
    return None

print("=== enclosing functions ===")
for va in (0x6292F0, 0x637930, 0x62DD60, 0x62F6F0, 0x632680, 0x6293B0, 0x6292B0):
    print("   %08X -> ~%s" % (va, ("%08X" % fs(va)) if fs(va) else "?"))

print()
print("=== all immediates of 0xD692ADA0 / 0xD692ADAB ===")
for val in (0xD692ADA0, 0xD692ADAB, 0xD692ADA1):
    n = 0
    for pre in (b"\x68", b"\xb8", b"\xb9", b"\xba", b"\xbb", b"\xbe", b"\xbf", b"\x81"):
        for o in pe.find_bytes(pre + struct.pack("<I", val)):
            v = pe.off_to_va(o)
            if v and pe.is_exec(v):
                n += 1
                print("   %08X  0x%08X  (prefix %s)" % (v, val, pre.hex()))
    print("   -- 0x%08X total=%d --" % (val, n))

print()
print("=== strings 0xDC7A10 / 0xDC7A28 / 0xDC7A3C / 0xDCA06C ===")
for va in (0xDC7A10, 0xDC7A28, 0xDC7A3C, 0xDCA06C, 0xDC66D0):
    print("   %08X %r" % (va, cstr(va)))

print()
print("=== callers of 0x6292B0 and 0x6293B0 ===")
for t in (0x6292B0, 0x6293B0):
    c = pe.calls_to(t)
    print("   0x%08X -> %d callers" % (t, len(c)))
    for v in c[:12]:
        print("      %08X (in ~%s)" % (v, ("%08X" % fs(v)) if fs(v) else "?"))
