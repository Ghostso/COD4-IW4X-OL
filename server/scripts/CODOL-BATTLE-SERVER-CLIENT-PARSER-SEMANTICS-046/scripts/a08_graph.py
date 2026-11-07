# -*- coding: utf-8 -*-
"""a08: callers/callees of the receive functions + string xrefs."""
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB

def s(rva, ml=300):
    b=C.raw(rva,ml)
    if b is None: return None
    e=b.find(b"\x00"); return b[:e].decode("latin1","replace")

# reference scan for a VA dword (lea/push/mov imm32)
def va_refs(va):
    pat=struct.pack("<I",va); out=[]; i=C._img.find(pat)
    while i>=0:
        if any(sec["raw"]<=i<sec["raw"]+sec["rsize"] for sec in C.SECS): out.append(i)
        i=C._img.find(pat,i+1)
    return out

print("=== all VA refs to 'udp://%s:%d' (VA 0xD85AB0) ===")
for r in va_refs(0xD85AB0): print("  0x%08X"%r)

print()
print("=== callers (E8) of key funcs ===")
for name, tgt in [("0x85D870 recv-fn",0x85D870),("0x85D5A0 init-fn",0x85D5A0),
                  ("0x85E6F0 TQOS-dispatch",0x85E6F0),("0x87BA50 thunk",0x87BA50),
                  ("0x87BE00 select+recv",0x87BE00),("0x87D5A0 decoder2",0x87D5A0),
                  ("0x87C110 decoder1",0x87C110),("0x85D430 setup",0x85D430),
                  ("0x85D2C4 s2",0x85D2C4),("0xC7B8F0 resolve",0xC7B8F0),
                  ("0xC7B8E0 close?",0xC7B8E0),("0xC7B8F0?",0xC7B8F0)]:
    cs=C.e8_callers(tgt)
    print("  %-22s %d callers: %s"%(name,len(cs),", ".join("0x%X"%a for a,_ in cs)))

print()
print("=== strings near 0x85D870 function refs (data referenced) ===")
# scan the function body for push/lea imm32 pointing to strings
lo,hi=0x85D870,0x85DA81
seen=set()
for i in range(lo,hi-4):
    # push imm32
    if C._img[i]==0x68:
        v=struct.unpack_from("<I",C._img,i+1)[0]
        if 0x900000<=v<0xE00000 and v not in seen:
            st=s(v-IB)
            if st and all(32<=ord(c)<127 for c in st[:6]):
                seen.add(v); print("  @0x%08X push 0x%08X -> %r"%(i,v,st))
