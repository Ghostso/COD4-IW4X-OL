from pathlib import Path
import pefile
from capstone import *
ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
p=ROOT/r"COD OL\codoMP_client_shipRetail.exe"; d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
def va2off(va):
 r=va-base
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):return s.PointerToRawData+r-s.VirtualAddress
 raise ValueError(hex(va))
print('SECTIONS')
for s in pe.sections: print(s.Name.rstrip(b'\0').decode(errors='replace'),hex(base+s.VirtualAddress),hex(s.PointerToRawData),hex(s.SizeOfRawData),hex(s.Characteristics))
lo=0x584c00; hi=0x585180
code=d[va2off(lo):va2off(hi)]
for i in Cs(CS_ARCH_X86,CS_MODE_32).disasm(code,lo): print('%08X %-24s %-8s %s'%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
print('\nIMPORTS around referenced IAT')
range_lo=0x6b2000; range_hi=0x6b4000
for ent in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]):
 dll=ent.dll.decode(errors='replace')
 for x in ent.imports or []:
  if range_lo<=x.address<range_hi: print(hex(x.address),dll,x.name.decode(errors='replace') if x.name else 'ORD'+str(x.ordinal))
