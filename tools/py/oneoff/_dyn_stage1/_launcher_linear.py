from pathlib import Path
import pefile
from capstone import *
p=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\WeGameLauncher\launcher.exe")
d=p.read_bytes();pe=pefile.PE(data=d,fast_load=True);base=pe.OPTIONAL_HEADER.ImageBase
sec=next(s for s in pe.sections if s.Name.rstrip(b"\0")==b".text");code=sec.get_data();cv=base+sec.VirtualAddress
md=Cs(CS_ARCH_X86,CS_MODE_32);md.skipdata=True
allins=list(md.disasm(code,cv))
for target in [0x411bb6,0x44b272,0x4171f6,0x417541,0x44b81d]:
 print("\n===== TARGET",hex(target),"=====")
 idx=next((i for i,x in enumerate(allins) if x.address<=target<x.address+max(1,len(x.bytes))),None)
 if idx is None: print("not found");continue
 for ins in allins[max(0,idx-50):idx+35]:
  mark=">>" if ins.address<=target<ins.address+len(ins.bytes) else "  "
  print("%s%08X %-20s %-7s %s"%(mark,ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
