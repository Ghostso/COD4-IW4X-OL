import pefile
SAMP={
 "S-2697 (SERVER)": r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe",
 "C-2697 (CLIENT shipped)": r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe",
 "C-2697-Rec (CLIENT recovered)": r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin",
}
for lbl,P in SAMP.items():
    pe=pefile.PE(P,fast_load=True)
    print("== %s ==" % lbl)
    print("   size=%d ImageBase=0x%X SizeOfImage=0x%X EP=0x%X" % (
        __import__('os').path.getsize(P), pe.OPTIONAL_HEADER.ImageBase,
        pe.OPTIONAL_HEADER.SizeOfImage, pe.OPTIONAL_HEADER.AddressOfEntryPoint))
    print("   sections: %s" % [(s.Name.rstrip(b"\0").decode(), hex(s.VirtualAddress), hex(s.Misc_VirtualSize)) for s in pe.sections])
    # does RVA 0xA0807 lie in a section of this binary?
    for rva in (0xA0807, 0xA0997, 0xA0468):
        hit=None
        for s in pe.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
                hit=(s.Name.rstrip(b"\0").decode(), rva-s.VirtualAddress)
        print("   RVA 0x%X -> %s" % (rva, hit if hit else "NOT MAPPED"))
    print()