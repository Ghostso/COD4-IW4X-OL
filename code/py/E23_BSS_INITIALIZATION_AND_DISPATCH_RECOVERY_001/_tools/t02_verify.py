import sys, struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def sec_of(r):
    for n,va,vs,rp,rs in secs:
        if va<=r<va+vs: return (n,va,vs,rp,rs)
def off_of(r):
    s=sec_of(r)
    if not s: return None
    n,va,vs,rp,rs=s
    if rs==0 or r-va>=rs: return None
    return rp+r-va
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# Verify the raw encodings of the call sites seen in E22 intermediates
CAMEL=[(0x6AC168,"e86399fdff","call target?"),(0x6AC22C,"e80f94fdff",""),(0x6AC2BC,"e81f99fdff",""),(0x6AC37B,"e86098fdff",""),(0x6AAEF4,"e8a7c9fdff",""),(0x6AAF22,"e879c9fdff","")]
print("== rel32 recomputation (caller RVA -> target VA/RVA) ==")
for rva,hexb,note in CAMEL:
    b=bytes.fromhex(hexb)
    ins_va=IB+rva
    nxt=ins_va+5
    rel=struct.unpack_from('<i',b,1)[0]
    tgt=(nxt+rel)&0xffffffff
    print("caller RVA %06X VA %08X bytes %s rel=%+d target VA %08X target RVA %06X -> sec=%s raw=%s"%(
        rva,ins_va,hexb,rel,tgt,tgt-IB,sec_of(tgt-IB)[0] if sec_of(tgt-IB) else None, hex(off_of(tgt-IB)) if off_of(tgt-IB) is not None else None))
print()
print("== five targets interpreted BOTH ways ==")
for a in (0xA85AD0,0xA85BE0,0xA85640,0xA87830,0xA878A0):
    as_rva=sec_of(a); as_va=sec_of(a-IB)
    print("%08X  as-RVA: sec=%s raw=%s |  as-VA: rva=%06X sec=%s raw=%s"%(
        a, as_rva[0] if as_rva else None, (hex(off_of(a)) if off_of(a) is not None else None),
        a-IB, as_va[0] if as_va else None, (hex(off_of(a-IB)) if off_of(a-IB) is not None else None)))
