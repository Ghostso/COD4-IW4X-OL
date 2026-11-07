from pathlib import Path
import pefile
from capstone import *
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
rel=r"COD OL\TenProxy.dll"; p=root/rel; d=p.read_bytes(); pe=pefile.PE(data=d)
base=pe.OPTIONAL_HEADER.ImageBase
print("base",hex(base),"entry",hex(base+pe.OPTIONAL_HEADER.AddressOfEntryPoint))
for s in pe.sections: print("SEC",s.Name.rstrip(b"\0"),hex(base+s.VirtualAddress),hex(s.PointerToRawData),hex(s.SizeOfRawData))
for tar in [0x100061e2,0x100060ef,0x10006273,0x100077a1,0x10009a95]:
 sec=next(s for s in pe.sections if base+s.VirtualAddress<=tar<base+s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData))
 va=base+sec.VirtualAddress; start=max(va,tar-300); end=min(va+s.SizeOfRawData,tar+300)
 blob=d[sec.PointerToRawData+(start-va):sec.PointerToRawData+(end-va)]
 print("=====",hex(tar))
 md=Cs(CS_ARCH_X86,CS_MODE_32)
 for i in md.disasm(blob,start):
  print((">>" if abs(i.address-tar)<=8 else "  "),"%08x %-18s %s %s"%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
