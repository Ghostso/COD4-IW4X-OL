from pathlib import Path
import pefile
from capstone import *
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
d=(root/r"WeGame\tgp_daemon.exe").read_bytes(); pe=pefile.PE(data=d,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
def raw(a):
 s=next(s for s in pe.sections if base+s.VirtualAddress<=a<base+s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData))
 return s.PointerToRawData+(a-(base+s.VirtualAddress))
def dump(a,delta=256):
 start=a-delta; blob=d[raw(start):raw(a+delta)]
 print("=====",hex(a))
 md=Cs(CS_ARCH_X86,CS_MODE_32)
 for i in md.disasm(blob,start):
  print((">>" if i.address==a else "  "),"%08x %-20s %s %s"%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
for a in [0x4a1e94,0x49fdcd,0x4949cc]: dump(a)
