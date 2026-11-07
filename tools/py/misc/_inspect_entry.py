import pefile
from pathlib import Path
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes()
p=pefile.PE("COD OL/codoMP_client_shipRetail.exe")
print("imagebase",hex(p.OPTIONAL_HEADER.ImageBase),"entry",hex(p.OPTIONAL_HEADER.AddressOfEntryPoint))
for s in p.sections: print(s.Name,hex(s.VirtualAddress),hex(s.Misc_VirtualSize),hex(s.PointerToRawData),hex(s.SizeOfRawData),hex(s.Characteristics))
for pat in (bytes.fromhex("ff151481ca00"),bytes.fromhex("ff159481ca00")):
 print("pattern",pat.hex())
 pos=0
 while True:
  i=D.find(pat,pos)
  if i<0:break
  print("fileoff",hex(i),"rva",hex(p.get_rva_from_offset(i) or 0),p.get_section_by_offset(i).Name if p.get_section_by_offset(i) else None)
  pos=i+1

