# -*- coding: utf-8 -*-
import sys,struct,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
print("=== strings near 0xB9C15B / 0xB9C1A6 (SEH scope tables) ===")
for va in (0xB9C15B,0xB9C1A6,0xC9F794):
    b=C.bytes_rva(va-0x400000,64)
    print("  0x%X %r"%(va,b[:48] if b else None))
print()
print("=== vtable @0xC9F794 ===")
o,_=C.off(0xC9F794-0x400000)
for i in range(6):
    v=struct.unpack_from("<I",C.d,o+i*4)[0]
    print("   [%d] 0x%08X (RVA 0x%X)"%(i,v,(v-0x400000)&0xffffffff))
print()
print("=== strings in .rdata near C9F700..C9FA00 ===")
o2,_=C.off(0xC9F700-0x400000)
raw=C.d[o2:o2+0x300]
for m in re.finditer(rb"[ -~]{6,}",raw):
    print("   0x%X %r"%(0x400000+0xC9F700-0x400000+m.start(), m.group()[:70]))
