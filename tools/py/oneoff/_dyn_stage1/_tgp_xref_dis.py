from pathlib import Path
import pefile
from capstone import *
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
def get(rel,center,delta=256):
 d=(root/rel).read_bytes(); pe=pefile.PE(data=d,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
 sec=next(s for s in pe.sections if base+s.VirtualAddress<=center<base+s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData))
 va=base+sec.VirtualAddress; raw=sec.PointerToRawData
 start=max(va,center-delta); end=min(va+sec.SizeOfRawData,center+delta)
 blob=d[raw+(start-va):raw+(end-va)]
 print("=====",rel,hex(center),"mapped",hex(start),hex(end))
 md=Cs(CS_ARCH_X86,CS_MODE_32)
 for i in md.disasm(blob,start):
  mark=">>" if abs(i.address-center)<=8 else "  "
  print("%s %08x %-20s %s %s"%(mark,i.address,i.bytes.hex(),i.mnemonic,i.op_str))
for a in [0x4949cc,0x49fdcd,0x4a1e94,0x499c8a,0x4a0a59]: get(r"WeGame\tgp_daemon.exe",a)
