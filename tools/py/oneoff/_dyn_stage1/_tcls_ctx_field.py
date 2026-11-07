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
def find_patterns(patterns):
 for s in pe.sections:
  if not (s.Characteristics & 0x20000000): continue
  b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; va=base+s.VirtualAddress
  for pat in patterns:
   for i in range(len(b)-len(pat)):
    if b[i:i+len(pat)]==pat: print("PAT",pat.hex(),"AT",hex(va+i))
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
# dump callers of 47419b
for x in [0x477109,0x477c32]:
 st=x
 for y in range(x-1,max(base,x-0x500),-1):
  try:
   if d[voff(y):voff(y)+3]==b"\x55\x8b\xec": st=y; break
  except: pass
 print("CALLER",hex(x),"START",hex(st)); dump(st,min(0x600,x-st+0x100))
# find accesses to [reg+0x8c] as push/mov around constructors, and likely string-assignment calls
print("FIELD 8C")
for s in pe.sections:
 if not (s.Characteristics & 0x20000000): continue
 b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; va=base+s.VirtualAddress
 for i in range(len(b)-4):
  # push dword ptr [eax+0x8c], [ecx+0x8c], [edx+0x8c]
  if b[i]==0xff and b[i+1] in (0xb0,0xb1,0xb2) and b[i+2]==0x8c:
   print("PUSH8C",hex(va+i))
