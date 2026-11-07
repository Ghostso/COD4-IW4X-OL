import pefile, struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
n,va,vs,rp,rs=[s for s in secs if s[0]==".text"][0]
tdata=d[rp:rp+rs]
def calls(t):
    out=[]
    for i in range(len(tdata)-5):
        if tdata[i]==0xe8:
            rel=struct.unpack_from('<i',tdata,i+1)[0]
            if ((IB+va+i+5+rel)&0xffffffff)==t: out.append(va+i)
    return out
for t in (0x6AB310,0x6AAE70,0x6AC0C0,0x6AB9D8,0xA87BA0,0xA87D50,0xA87C30):
    print("callers of %08X:"%t,[hex(x) for x in calls(t)])
