import pefile, struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def f2rva(o):
    for n,va,vs,rp,rs in secs:
        if rp<=o<rp+rs: return va+(o-rp),n
    return None,None
for label,va in [("send",0xBAE4C8),("sendto",0xBAE504),("recv",0xBAE490),("recvfrom",0xBAE50C)]:
    pat=struct.pack("<I",va)
    hits=[]; i=0
    while True:
        j=d.find(pat,i)
        if j<0: break
        r,n=f2rva(j)
        if n in (".text",".tvm0"): hits.append((r,n))
        i=j+1
    print("%-9s VA %08X : %d refs in code"%(label,va,len(hits)))
    for r,n in hits[:30]: print("    RVA %06X %s"%(r,n))
