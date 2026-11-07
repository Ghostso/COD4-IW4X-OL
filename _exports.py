import pefile
p=pefile.PE("COD OL/codoMP_client_shipRetail.exe")
for e in p.DIRECTORY_ENTRY_EXPORT.symbols:
 print(hex(e.address),e.name,e.ordinal)

