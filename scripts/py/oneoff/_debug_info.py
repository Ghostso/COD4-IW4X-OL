import pefile
p=pefile.PE("COD OL/codoMP_client_shipRetail.exe")
for d in p.DIRECTORY_ENTRY_DEBUG:
 s=d.struct
 data=p.__data__[s.PointerToRawData:s.PointerToRawData+s.SizeOfData]
 print("type",s.Type,"size",hex(s.SizeOfData),"rva",hex(s.AddressOfRawData),"raw",hex(s.PointerToRawData))
 print(data.hex(" "))
 print("ascii", "".join(chr(x) if 32<=x<127 else "." for x in data))
