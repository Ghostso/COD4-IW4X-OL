import pefile
p=pefile.PE(r'COD OL\codoMP_client_shipRetail.exe',fast_load=True)
print(hex(p.OPTIONAL_HEADER.ImageBase),hex(p.OPTIONAL_HEADER.AddressOfEntryPoint),hex(p.OPTIONAL_HEADER.SizeOfImage))
for s in p.sections:
    print(s.Name.rstrip(b'\0').decode('latin1'),hex(s.VirtualAddress),hex(s.SizeOfRawData),hex(s.PointerToRawData))
