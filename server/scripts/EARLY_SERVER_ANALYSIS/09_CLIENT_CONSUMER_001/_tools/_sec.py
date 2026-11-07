import pefile
p=r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
pe=pefile.PE(p, fast_load=True)
print("ImageBase", hex(pe.OPTIONAL_HEADER.ImageBase))
for s in pe.sections:
    print(s.Name.rstrip(b"\x00").decode(errors="replace"), "VA",hex(s.VirtualAddress),"vsize",hex(s.Misc_VirtualSize),"raw",hex(s.PointerToRawData),"rawsize",hex(s.SizeOfRawData))
# map file offset 0x8479ac and 0x938d8
for off in (0x8479ac,0x938d8,0x9cd5f):
    print("off",hex(off),"->",hex(pe.OPTIONAL_HEADER.ImageBase+pe.get_rva_from_offset(off)))
