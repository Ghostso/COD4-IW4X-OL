import pefile,sys
packed=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
pe=pefile.PE(packed, fast_load=True)
print("packed ImageBase",hex(pe.OPTIONAL_HEADER.ImageBase),"SizeOfImage",hex(pe.OPTIONAL_HEADER.SizeOfImage),"Entry",hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
for s in pe.sections:
    print("  %-8s VA %08X VS %08X raw %08X rs %08X ch %08X"%(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData,s.Characteristics))
d=open(packed,"rb").read()
def at(va,n=16):
    rva=va-pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
            off=s.PointerToRawData+(rva-s.VirtualAddress)
            return d[off:off+n].hex(" ")
    return None
for va in (0x6AB310,0x6AB8C5,0x6AB907,0x9CE310,0x7C6DA60,0x9BAFD0,0x703A00,0xA2E880):
    print("  %08X %s"%(va,at(va)))
