from pathlib import Path
import pefile, struct
from capstone import *
ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
d=(ROOT/r"WeGame\tcls\tcls_core.exe").read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
def voff(va):
 r=va-base
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData): return s.PointerToRawData+r-s.VirtualAddress
 raise ValueError(hex(va))
def dis(va,n):
 return list(Cs(CS_ARCH_X86,CS_MODE_32).disasm(d[voff(va):voff(va)+n],va))
def calls_to(target):
 xs=[]
 for s in pe.sections:
  if not (s.Characteristics & 0x20000000): continue
  b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; va=base+s.VirtualAddress
  for off in range(len(b)-5):
   if b[off]==0xe8:
    src=va+off; dst=(src+5+struct.unpack_from("<i",b,off+1)[0])&0xffffffff
    if dst==target: xs.append(src)
 return xs
def prologue(x):
 for y in range(x-1,max(base,x-0x800),-1):
  try:
   if d[voff(y):voff(y)+3]==b"\x55\x8b\xec": return y
  except: pass
 return x
def dump(va,n):
 print("=====",hex(va),hex(va+n))
 for i in dis(va,n): print("%08X %-20s %-7s %s"%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
# exact xref targets to callers 477109,477c32
for t in [0x477109,0x477c32]:
 xs=[]
 for s in pe.sections:
  if not (s.Characteristics & 0x20000000): continue
  b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; va=base+s.VirtualAddress
  for x in calls_to(t):
   xs.append(x)
 print("CALLS_TO",hex(t),[hex(x) for x in xs])
 for x in xs:
  st=prologue(x); print("PARENT",hex(st),hex(x)); dump(st,min(0x500,x-st+0x100))
# 471299 and 4774d2 contexts
for x in [0x471299,0x4774d2,0x47806a]:
 print("CTX",hex(x)); dump(x-96,256)
