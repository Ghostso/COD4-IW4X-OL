# -*- coding: utf-8 -*-
"""Find {string_ptr, code_ptr} / {code_ptr, string_ptr} pairs = CoD-style handler tables.
Read-only."""
import sys, os, struct, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
b=C._b
CODE_LO,CODE_HI=0x1000,0x8a8000
STR_LO,STR_HI=0x8a8000,0xa65000
def is_str(va):
    r=va-C.IB
    if not (STR_LO<=r<STR_HI): return None
    o=r
    if o+3>=len(b): return None
    e=b.find(b"\0",o,o+64)
    if e<0 or e-o<3: return None
    s=b[o:e]
    if all(32<=c<127 for c in s): return s.decode("latin1")
    return None
def is_code(va):
    r=va-C.IB
    return CODE_LO<=r<CODE_HI
res=[]
lo,hi=STR_LO,STR_HI
i=lo
while i<hi-8:
    v1=struct.unpack("<I",b[i:i+4])[0]
    v2=struct.unpack("<I",b[i+4:i+8])[0]
    s=is_str(v1)
    if s and is_code(v2):
        res.append((i,s,v2-C.IB,"name,code"))
    s2=is_str(v2)
    if s2 and is_code(v1):
        res.append((i,s2,v1-C.IB,"code,name"))
    i+=4
o=io.open(os.path.join(C.EV,"name_code_tables.txt"),"w",encoding="utf-8",newline="")
o.write("count=%d\n"%len(res))
for off,s,crv,kind in res[:400]:
    o.write("  %08x %-6s name=%-40s code=%08x\n"%(off,kind,s[:40],crv))
o.close()
print("pairs found:", len(res))
# print ones whose name looks network/command-ish
import re
KW=re.compile(r"(connect|challenge|heartbeat|info|user|stat|cmd|msg|packet|net|server|client|move|snapshot|gamestate|config|print|disconnect|echo|map|team|chat)",re.I)
sel=[x for x in res if KW.search(x[1])]
print("command-ish pairs:", len(sel))
for off,s,crv,kind in sel[:80]:
    print("  %08x %-6s %-40s -> %08x"%(off,kind,s[:40],crv))
