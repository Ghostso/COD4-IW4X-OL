from pathlib import Path
import pefile
from capstone import *
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
rel=r"WeGame\tcls\tcls_core.exe"
p=root/rel; d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
# map IAT VA -> imported name
imp={}
for e in pe.DIRECTORY_ENTRY_IMPORT:
 for i in (e.imports or []):
  if i.name: imp[base+i.address]=i.name.decode(errors="replace")
print("IMPORT_COUNT",len(imp))
for a,n in sorted(imp.items()):
 if any(k in n for k in ["Mapping","MapView","Process","CommandLine","Mutex"]): print("IAT",hex(a),n)
# exact UTF16 / ASCII targeted strings
terms=[b"TCLS_SHAREDMEMEMORY",b"TCLS_TASMEMORY_",b"TP3GameGuardShareMapping",b"TPUSERACCOUNT_SHAREDMEMEMORY",b"TCLS",b"tcls_core",b"cmd_start_for.ini",b"cmd_launcher_info.ini",b"StartFor",b"AddPath"]
for t in terms:
 for enc in ["ascii","utf16le"]:
  q=t if enc=="ascii" else t.decode().encode("utf-16le")
  hits=[];i=0
  while True:
   i=d.find(q,i)
   if i<0:break
   hits.append(i);i+=1
  if hits:
   print("TERM",enc,t.decode(),[hex(x) for x in hits])
   for o in hits:
    try: print("  VA",hex(base+pe.get_rva_from_offset(o)))
    except: pass
# function windows
def raw(a):
 s=next(s for s in pe.sections if base+s.VirtualAddress<=a<base+s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData))
 return s.PointerToRawData+a-(base+s.VirtualAddress)
def find_start(target,maxback=0x300):
 for x in range(target,max(target-maxback,base),-1):
  if d[raw(x):raw(x)+3]==b"\x55\x8b\xec": return x
 return target-0x100
for target in [0x407d81,0x407ed1,0x40c2b8,0x40c4f7,0x41e745,0x41e76a,0x47a76c,0x497c86,0x497c9e,0x497d16,0x497d1c]:
 start=find_start(target,0x500); end=target+0x120
 blob=d[raw(start):raw(end)]
 print("=====",hex(target),"start",hex(start))
 md=Cs(CS_ARCH_X86,CS_MODE_32)
 for ins in md.disasm(blob,start):
  ann=""
  if ins.mnemonic=="call":
   ops=ins.op_str
   if ops.startswith("dword ptr [") and ops.endswith("]"):
    try: ann=" ; "+imp.get(int(ops[12:-1],16),"")
    except: pass
  print((">>" if abs(ins.address-target)<=8 else "  "),"%08x %-20s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann))
