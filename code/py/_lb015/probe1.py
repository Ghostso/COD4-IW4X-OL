import pefile, struct
p = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
pe = pefile.PE(p, fast_load=True)
print("ImageBase", hex(pe.OPTIONAL_HEADER.ImageBase))
print("SizeOfImage", hex(pe.OPTIONAL_HEADER.SizeOfImage))
print("EntryPoint", hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
for s in pe.sections:
    print(repr(s.Name), "VA=%08X" % s.VirtualAddress, "VS=%08X" % s.Misc_VirtualSize,
          "RAW=%08X" % s.PointerToRawData, "RS=%08X" % s.SizeOfRawData, "flag=%08X" % s.Characteristics)
