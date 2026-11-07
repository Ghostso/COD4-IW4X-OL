import pefile  
p=pefile.PE(r'COD OL/codoMP_client_shipRetail.exe')  
raw=0x6c7f80  
rva=p.get_rva_from_offset(raw)  
print(hex(raw),hex(rva),hex(p.OPTIONAL_HEADER.ImageBase+rva))  
