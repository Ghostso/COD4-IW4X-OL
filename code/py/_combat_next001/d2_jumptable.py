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

print("=== jump table at 0x5C0F3C (4 entries) ===")
for i in range(4):
    v = struct.unpack("<I", pe.read(0x5C0F3C + i*4, 4))[0]
    print("   case[%d] -> %08X" % (i, v))
print()
print("=== strings in the 4 case targets ===")
for i in range(4):
    t = struct.unpack("<I", pe.read(0x5C0F3C + i*4, 4))[0]
    b = pe.read(t, 400)
    # 找出这一段内的 push imm32 字符串引用
    found = []
    for k in range(len(b) - 5):
        if b[k] == 0x68 or b[k] in (0xBA, 0xB8, 0xB9, 0xBB, 0xBE, 0xBF):
            v = struct.unpack_from("<I", b, k+1)[0]
            if 0xD00000 <= v <= 0xE60000:
                s = cstr(v)
                if s and len(s) > 2:
                    found.append(hex(v) + "=" + repr(s[:50]))
    print("   case[%d] %08X: %s" % (i, t, "; ".join(found[:12])))
print()
print("=== 0x67511F tail is 'post message'; callers of 0x675260 ===")
for va in pe.calls_to(0x675260):
    print("   %08X" % va)
print()
print("=== the address the tail posts to: 0xCA8128 context ===")
print("bytes at 0xCA8120..0xCA8140: " + pe.read(0xCA8120, 32).hex())
