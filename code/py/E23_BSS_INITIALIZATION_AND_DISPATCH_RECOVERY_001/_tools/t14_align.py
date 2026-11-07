import sys, struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
n,va,vs,rp,rs=[s for s in secs if s[0]==".text"][0]
tdata=d[rp:rp+rs]
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def rel_hits(t):
    hits=[]
    for i in range(len(tdata)-5):
        if tdata[i]==0xe8:
            rel=struct.unpack_from('<i',tdata,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==t: hits.append(va+i)
    return hits
def aligned(rva):
    # find preceding 0xCC run inside .text, disasm forward, check boundary at rva
    idx=rva-va
    j=idx
    while j>0 and tdata[j-1]==0xcc: j-=1
    start=va+j
    off=rp+j
    last=None
    for ins in md.disasm(tdata[j:j+(rva-va-j)+16],IB+start):
        last=ins
        if ins.address-IB==rva:
            return (True,last.mnemonic,last.op_str,start)
        if ins.address-IB>rva: break
    return (False,None,None,start)
for t in (0xA85AD0,0xA85BE0,0xA85640,0xA87830,0xA878A0):
    hs=rel_hits(t)
    ok=0; sample=[]
    for h in hs:
        a=aligned(h)
        if a[0]:
            ok+=1
            if len(sample)<6: sample.append(hex(h))
    print("VA %08X  rel32-E8 hits=%d  aligned-verified=%d  sample=%s"%(t,len(hs),ok,sample))
