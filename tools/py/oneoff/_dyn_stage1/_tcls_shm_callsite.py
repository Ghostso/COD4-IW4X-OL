from pathlib import Path
import pefile, struct
from capstone import *
ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
d=(ROOT/r"WeGame\tcls\tcls_core.exe").read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
imp={}
for e in pe.DIRECTORY_ENTRY_IMPORT:
 for x in e.imports or []:
  imp[x.address]=x.name.decode(errors="replace") if x.name else ("ORD_%s"%x.ordinal)
def voff(va):
 r=va-base
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData): return s.PointerToRawData+r-s.VirtualAddress
 raise ValueError(hex(va))
def dump(va,n):
 print("=====",hex(va),hex(va+n))
 for i in Cs(CS_ARCH_X86,CS_MODE_32).disasm(d[voff(va):voff(va)+n],va):
  ann=""
  if i.mnemonic in ("call","jmp") and i.op_str.startswith("dword ptr ["):
   try: ann=imp.get(int(i.op_str[12:-1],16),"")
   except: pass
  print("%08X %-22s %-7s %-32s %s"%(i.address,i.bytes.hex(),i.mnemonic,i.op_str,ann))
def callxrefs(target):
 xs=[]
 for s in pe.sections:
  if not (s.Characteristics & 0x20000000): continue
  b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; va=base+s.VirtualAddress
  for off in range(len(b)-5):
   if b[off]==0xE8:
    src=va+off; dest=(src+5+struct.unpack_from("<i",b,off+1)[0]) & 0xffffffff
    if dest==target: xs.append(src)
 return xs
for fn in range(0x4743A7-0x120,0x4743A7+0x10):
 pass
dump(0x4742c0,0x130)
# find all virtual calls [reg+0xc0] nearby
print("VCALL_C0")
for i in Cs(CS_ARCH_X86,CS_MODE_32).disasm(d[voff(0x474000):voff(0x474800)],0x474000):
 if i.mnemonic=="call" and "+ 0xc0]" in i.op_str: print(hex(i.address),i.op_str)
# xrefs of function 0x47419b
print("XREF 47419b")
for x in callxrefs(0x47419b): print(hex(x))
