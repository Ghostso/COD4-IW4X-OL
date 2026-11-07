import pefile
for P in [r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"]:
    pe=pefile.PE(P,fast_load=True)
    print("== ORIGINAL packed client ==")
    print("ImageBase 0x%X EP 0x%X SizeOfImage 0x%X" % (pe.OPTIONAL_HEADER.ImageBase,pe.OPTIONAL_HEADER.AddressOfEntryPoint,pe.OPTIONAL_HEADER.SizeOfImage))
    for s in pe.sections:
        print("  %-9s VA=0x%08X VSize=0x%08X RawPtr=0x%08X RawSize=0x%08X" % (
            s.Name.rstrip(b"\x00").decode(),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData))