# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
def rdstr(rva, wide=False):
    b=C.raw(rva,256)
    if b is None: return None
    if wide:
        e=b.find(b"\x00\x00"); 
        if e>0 and e%2: e+=1
        return b[:e].decode("utf-16le","replace")
    e=b.find(b"\x00")
    return b[:e].decode("latin1","replace")
for a in (0xD85AB0,):
    print("str @0x%X = %r"%(a, rdstr(a)))
    print("wide @0x%X = %r"%(a, rdstr(a,True)))
print()
print("=== dump func 0x85D870..0x85DA81 (full) ===")
print(C.dump(0x85D870,0x85DA81))
