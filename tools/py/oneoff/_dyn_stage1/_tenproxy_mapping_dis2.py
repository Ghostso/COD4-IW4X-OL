from pathlib import Path
import pefile
from capstone import *
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
for rel,targets in [(r"COD OL\TenProxy.dll",[0x100061e2,0x100060ef,0x10006273,0x100077a1,0x10009a95])]:
 d=(root/rel).read_bytes(); pe=pefile.PE(data=d); base=pe.OPTIONAL_HEADER.ImageBase
 def raw(a):
  s=next(s for s in pe.sections if base+s.VirtualAddress<=a<base+s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData))
  return s.PointerToRawData+a-(base+s.VirtualAddress)
 for tar in targets:
  start=tar-240; blob=d[raw(start):raw(tar+240)]
  print("=====",hex(tar))
  md=Cs(CS_ARCH_X86,CS_MODE_32)
  for i in md.disasm(blob,start):
   if start-20<=i.address<=tar+180: print((">>" if abs(i.address-tar)<=8 else "  "),"%08x %-18s %s %s"%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
