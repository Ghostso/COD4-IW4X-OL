# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
def s(rva, ml=400):
    b=C.raw(rva,ml)
    if b is None: return None
    e=b.find(b"\x00"); return b[:e].decode("latin1","replace")
print("=== string literals referenced (push/lea imm32) in 0x85D2E0..0x85EC00 ===")
lo,hi=0x85D2E0,0x85EC00
seen={}
for i in range(lo,hi-5):
    op=C._img[i]
    v=None
    if op==0x68: v=struct.unpack_from("<I",C._img,i+1)[0]
    elif op==0x8D and C._img[i+1]==0x0D: v=struct.unpack_from("<I",C._img,i+2)[0]  # lea ecx
    elif op==0x8D and C._img[i+1]==0x05: v=struct.unpack_from("<I",C._img,i+2)[0]  # lea eax
    elif op==0x8D and C._img[i+1]==0x15: v=struct.unpack_from("<I",C._img,i+2)[0]  # lea edx
    if v and 0x900000<=v<0xE00000:
        st=s(v-IB)
        if st and len(st)>2 and all(32<=ord(c)<127 for c in st[:4]):
            seen.setdefault(v,(st,i))
for v,(st,i) in sorted(seen.items()):
    print("  0x%08X  (%s @0x%08X)"%(v,repr(st),i))
