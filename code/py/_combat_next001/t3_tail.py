# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()

def cstr(va, maxn=90):
    b = pe.read(va, maxn)
    if not b: return None
    z = b.find(b"\0")
    return b[:z if z >= 0 else maxn].decode("latin1", "replace")

print("=== 0x7F44B0 tail (after the 0xB9B0B0 call) : what does it do with the buffer? ===")
for l in pe.dis(0x7F4550, 60):
    print(l)
print()
print("=== 'sessionid' / netchan-related strings near 0x82E14xx users ===")
for k in ("sessionid","sessionId","SessionId","netchan","mmbook","mmstart","reserve","Reserve"):
    for off, va in pe.find_cstr(k)[:3]:
        print("   %-10s %08X %r" % (k, va, cstr(va)))
