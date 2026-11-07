import sys, struct, bisect, pickle
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E21_CRYPTO_PAYLOAD_CONSUMER_ATTRIBUTION_001\_tools")
from pe_helper import PE
from capstone import *
P = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C = PE(P); md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def disasm(a,n,tag):
    print("="*72); print(tag, hex(a), hex(a+n)); print("-"*72)
    o,_=C.off(a)
    for ins in md.disasm(C.d[o:o+n], C.IB+a):
        print("%06X %-22s %s %s"%(ins.address-C.IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
disasm(0x6A84E0,0x130,"0x6A84E0 ctor")
disasm(0x6A9720,0x100,"0x6A9720 second object ctor")
# vtable slots
for va in (0xC5B0A4,0xCBBD1C):
    rva=va-C.IB; o,nm=C.off(rva)
    slots=[struct.unpack_from("<I",C.d,o+4*i)[0] for i in range(8)] if o is not None else []
    print("VTABLE",hex(va),hex(rva),nm,[hex(x) for x in slots])
# nearby readable strings
for rva in (0x85B000,0x85B0A0,0x8BB000,0x8BBD00):
    o,nm=C.off(rva)
    if o is None: continue
    b=C.d[o:o+0x300]
    parts=[x for x in b.split(b"\0") if 5<=len(x)<=80 and all(32<=c<127 for c in x)]
    print("STRINGS",hex(rva),parts[:20])
print("IMAGEBASE",hex(C.IB))
print("SECTIONS",C.secs)
