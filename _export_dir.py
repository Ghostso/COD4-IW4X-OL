import pefile
p=pefile.PE("COD OL/codoMP_client_shipRetail.exe")
e=p.OPTIONAL_HEADER.DATA_DIRECTORY[0]
print("export",hex(e.VirtualAddress),hex(e.Size))
b=p.get_data(e.VirtualAddress,e.Size)
print(len(b),b[:128].hex())

