import sys, struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
print("ImageBase",hex(IB))
print("SizeOfImage",hex(pe.OPTIONAL_HEADER.SizeOfImage))
secs=[]
for s in pe.sections:
    secs.append((s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData,bool(s.Characteristics&0x20000000)))
for n,va,vs,rp,rs,x in secs:
    print("%-8s VA=%08X VS=%08X RAWoff=%08X RAWsz=%08X end=%08X raw_end=%08X exec=%s"%(n,va,vs,rp,rs,va+vs,va+rs,x))
def sec_of(r):
    for n,va,vs,rp,rs,x in secs:
        if va<=r<va+vs: return (n,va,vs,rp,rs,x)
    return None
def off_of(r):
    s=sec_of(r)
    if not s: return None
    n,va,vs,rp,rs,x=s
    if rs==0 or r-va>=rs: return None
    return rp+r-va
TARGETS=[0xA85AD0,0xA85BE0,0xA85640,0xA87830,0xA878A0]
print("\n== TARGETS as RVA ==")
for t in TARGETS:
    s=sec_of(t); o=off_of(t)
    print("RVA %08X  VA %08X  sec=%s  raw_off=%s  in_raw=%s"%(t,t+IB,s[0] if s else None,hex(o) if o is not None else None,o is not None))
print("\n== TARGETS as VA (rva = va-IB) ==")
for t in TARGETS:
    r=t-IB; s=sec_of(r); o=off_of(r)
    print("VA %08X  RVA %08X  sec=%s  raw_off=%s"%(t,r,s[0] if s else None,hex(o) if o is not None else None))
