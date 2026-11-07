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
def prologue(x):
 for y in range(x-1,max(base,x-0x400),-1):
  try:
   if d[voff(y):voff(y)+3]==b"\x55\x8b\xec": return y
  except: pass
 return x
for target in [0x404020,0x4078f0,0x407d10,0x4077f0]:
 xs=callxrefs(target); print("CALLX",hex(target),[hex(x) for x in xs])
 for x in xs:
  st=prologue(x); print("CALLER_FUNC_START",hex(st),"CALLSITE",hex(x)); dump(st,min(0x500,(x-st)+0x100))
