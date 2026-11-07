from pathlib import Path
import pefile, struct
from capstone import *
ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
p=ROOT/r"COD OL\TenProxy.dll"; d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
print("IMAGE",hex(base),"entry",hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
print("SECTIONS")
for s in pe.sections:
 print(s.Name.rstrip(b'\0').decode(errors='replace'),hex(base+s.VirtualAddress),hex(s.Misc_VirtualSize),hex(s.Characteristics))
print("IMPORTS AROUND 0x10026380")
for ent in pe.DIRECTORY_ENTRY_IMPORT:
 dll=ent.dll.decode(errors='replace')
 for x in ent.imports or []:
  if 0x10026370 <= x.address <= 0x100263d0:
   print(hex(x.address),dll,x.name.decode(errors='replace') if x.name else 'ORD'+str(x.ordinal))
print("EXPORTS")
exports=[]
if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
 for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
  name=e.name.decode(errors='replace') if e.name else 'ORD'+str(e.ordinal)
  exports.append((e.address,name))
  print(hex(base+e.address),name)
def va2off(va):
 r=va-base
 for s in pe.sections:
  if s.VirtualAddress <= r < s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData): return s.PointerToRawData+r-s.VirtualAddress
 raise ValueError(hex(va))
def dis(va,n):
 return list(Cs(CS_ARCH_X86,CS_MODE_32).disasm(d[va2off(va):va2off(va)+n],va))
def dump(va,n): 
 for i in dis(va,n): print("%08X %-24s %-8s %s"%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
# find function start before 10006176 by scanning byte prologues
for target in [0x10006176]:
 best=None
 for x in range(target-1,base-1,-1):
  try:b=d[va2off(x):va2off(x)+3]
  except:break
  if b==b'\x55\x8b\xec': best=x;break
 print("PROLOGUE",hex(best) if best else None)
 if best: dump(best,min(0x280,target-best+0x80))
# direct e8 calls to function around best or key addresses
def find_calls(t):
 out=[]
 for s in pe.sections:
  if not (s.Characteristics & 0x20000000): continue
  b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; sv=base+s.VirtualAddress
  for off in range(len(b)-5):
   if b[off]==0xe8:
    src=sv+off; dst=(src+5+struct.unpack_from('<i',b,off+1)[0])&0xffffffff
    if dst==t: out.append(src)
 return out
for addr,label in [(0x10006176,'str_short'),(best,'func_guess')]:
 if not addr: continue
 print("CALLS to",label,hex(addr),[hex(x) for x in find_calls(addr)])
