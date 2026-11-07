import sys, struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
TEXT=[s for s in secs if s[0]==".text"][0]
tn,tva,tvs,trp,trs=TEXT
tdata=d[trp:trp+trs]
# 1) rel32 call/jmp scanning for the 5 VA targets (absolute VA in instruction)
TVA=[0xA85AD0,0xA85BE0,0xA85640,0xA87830,0xA878A0]
print("=== rel32 call/jmp (E8/E9) resolving to the 5 VAs (whole .text) ===")
for t in TVA:
    hits=[]
    for i in range(len(tdata)-5):
        if tdata[i] in (0xe8,0xe9):
            rel=struct.unpack_from('<i',tdata,i+1)[0]
            dst=(IB+tva+i+5+rel)&0xffffffff
            if dst==t: hits.append((tva+i,tdata[i]))
    print("VA %08X (RVA %06X): %d hits ->"%(t,t-IB,len(hits)), [ (hex(r),hex(o)) for r,o in hits])
# 2) immediate absolute 32-bit references anywhere in .text (push imm32, mov reg,imm32)
print("\n=== any 4-byte little-endian occurrence of the VA constants across whole file ===")
for t in TVA:
    pat=struct.pack('<I',t)
    pos=[]; start=0
    while True:
        j=d.find(pat,start)
        if j<0: break
        pos.append(j); start=j+1
    # map file offset to section+rva
    def f2rva(o):
        for n,va,vs,rp,rs in secs:
            if rp<=o<rp+rs: return (n, va+(o-rp))
        return (None,o)
    info=[(hex(o), f2rva(o)[0], hex(f2rva(o)[1]) if f2rva(o)[0] else hex(o)) for o in pos]
    print("VA %08X: %d occurrences:"%(t,len(pos)), info[:20])
