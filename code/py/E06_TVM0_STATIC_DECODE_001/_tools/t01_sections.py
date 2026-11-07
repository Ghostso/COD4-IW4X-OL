import pefile, struct, math, collections
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
for lbl,P in (("ORIGINAL-PACKED",ORIG),("RECOVERED",REC)):
    data=open(P,"rb").read(); pe=pefile.PE(P,fast_load=True)
    print("==== %s ====  file=%d ImageBase=0x%X EP=0x%X SizeOfImage=0x%X" % (lbl,len(data),pe.OPTIONAL_HEADER.ImageBase,pe.OPTIONAL_HEADER.AddressOfEntryPoint,pe.OPTIONAL_HEADER.SizeOfImage))
    for s in pe.sections:
        nm=s.Name.rstrip(b"\x00").decode()
        if nm in (".tvm0",".rimin",".rimp") or "tvm" in nm or "rimp" in nm or "tp3" in nm:
            raw=data[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
            h=int(0xFFFFFFFF & pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress)
            print("  %-8s VA=0x%08X VSize=0x%08X RawPtr=0x%08X RawSize=0x%08X ratio=%.3f first32=%s" % (
                nm,s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData,
                s.Misc_VirtualSize/max(1,s.SizeOfRawData), raw[:32].hex(" ")))