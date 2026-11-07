import pefile, struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(P,"rb").read()
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
Smap={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
TARGET_RVA=0xA2E50
for nm in (".text",".tvm0"):
    va,vs,rp,rs=Smap[nm]; code=data[rp:rp+rs]; base_rva=va
    found=[]
    for i in range(len(code)-5):
        if code[i]==0xE8:
            disp=struct.unpack_from("<i",code,i+1)[0]
            call_site_rva=base_rva+i
            tgt_rva=call_site_rva+5+disp
            if tgt_rva==TARGET_RVA:
                found.append((call_site_rva, base_rva+i, disp))
    print("%-6s direct E8 -> RVA 0x%X : %d %s" % (nm,TARGET_RVA,len(found),[(hex(a)) for a,_,_ in found]))
print()
# Now list ALL distinct E8 targets in 0xA2000-0xA3000 with the call-site RVA
tgt={}
for nm in (".text",".tvm0"):
    va,vs,rp,rs=Smap[nm]; code=data[rp:rp+rs]; base_rva=va
    for i in range(len(code)-5):
        if code[i]==0xE8:
            disp=struct.unpack_from("<i",code,i+1)[0]
            t=base_rva+i+5+disp
            if 0xA2000<=t<0xA3000: tgt.setdefault(t,[]).append((nm,base_rva+i))
for t in sorted(tgt):
    print("  target RVA 0x%05X  <- %s" % (t, ["%s:0x%X"%(a,b) for a,b in tgt[t]]))