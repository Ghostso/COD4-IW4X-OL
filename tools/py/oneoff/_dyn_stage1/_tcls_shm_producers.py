from pathlib import Path
import pefile
from capstone import *
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
rel=r"WeGame\tcls\tcls_core.exe";d=(root/rel).read_bytes();pe=pefile.PE(data=d);base=pe.OPTIONAL_HEADER.ImageBase
imp={}
for e in pe.DIRECTORY_ENTRY_IMPORT:
 for i in (e.imports or []):
  if i.name: imp[base+i.address]=i.name.decode(errors="replace")
def raw(a):
 s=next(s for s in pe.sections if base+s.VirtualAddress<=a<base+s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData))
 return s.PointerToRawData+a-(base+s.VirtualAddress)
def range_dis(start,end):
 print("=====",hex(start),hex(end))
 md=Cs(CS_ARCH_X86,CS_MODE_32)
 for i in md.disasm(d[raw(start):raw(end)],start):
  ann=""
  if i.mnemonic in ("call","jmp") and "dword ptr [" in i.op_str:
   try: ann=" ; "+imp.get(int(i.op_str.split("[")[-1].split("]")[0],16),"")
   except: pass
  print("%08x %-20s %s %s%s"%(i.address,i.bytes.hex(),i.mnemonic,i.op_str,ann))
range_dis(0x404020,0x404260)
range_dis(0x4078f0,0x407b80)
