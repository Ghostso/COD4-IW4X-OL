from pathlib import Path
import pefile, struct
from capstone import *
ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
exe=ROOT/r"COD OL\codoMP_client_shipRetail.exe"
d=exe.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
img=pe.get_memory_mapped_image()
def voff(va):
 r=va-base
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData): return s.PointerToRawData+r-s.VirtualAddress
 raise ValueError(hex(va))
def cstr(va):
 o=voff(va); b=d[o:o+512]; return b.split(b"\0",1)[0].decode("latin1","replace")
def dump(va,n):
 print("=====",hex(va),hex(va+n))
 for i in Cs(CS_ARCH_X86,CS_MODE_32).disasm(img[va-base:va-base+n],va):
  print("%08X %-22s %-7s %s"%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
# scan rdata for format-like strings
print("STRINGS")
for s in pe.sections:
 if s.Name.rstrip(b"\0")!=b".rdata": continue
 b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
 for term in [b"WIN_NO_TCLS",b"IsTCLSLogOn",b"TCLS"]:
  p=0
  while True:
   i=b.find(term,p)
   if i<0: break
   print(term,hex(base+s.VirtualAddress+i))
   p=i+1
# immediate refs to WIN_NO_TCLS VA
target=0xddbf80
print("IMM_REFS")
for s in pe.sections:
 b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; va=base+s.VirtualAddress
 pat=struct.pack("<I",target)
 for i in range(len(b)-3):
  if b[i:i+4]==pat: print(hex(va+i))
# disasm around exact known string refs not found: scan code windows around every `push imm` that may be config string pointer by finding va literal
# Find all code refs into rdata around WIN_NO_TCLS and IsTCLSLogOn
for term in [0xddbf80,0xddd298,0xe763eb]:
 print("TERM",hex(term),"cstr",end=" ")
 try: print(repr(cstr(term)))
 except Exception as e: print(e)
 pat=struct.pack("<I",term)
 for s in pe.sections:
  if not (s.Characteristics & 0x20000000): continue
  b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; va=base+s.VirtualAddress
  start=0
  while True:
   i=b.find(pat,start)
   if i<0: break
   rv=va+i; print(" ref",hex(rv)); 
   try: dump(max(base,rv-96),256)
   except: pass
   start=i+1
