from pathlib import Path
import pefile,struct
from capstone import *
p=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\WeGameLauncher\launcher.exe")
d=p.read_bytes();pe=pefile.PE(data=d,fast_load=True);base=pe.OPTIONAL_HEADER.ImageBase;md=Cs(CS_ARCH_X86,CS_MODE_32)
sec=next(s for s in pe.sections if s.Name.rstrip(b"\0")==b".text");code=sec.get_data();cv=base+sec.VirtualAddress
for target in [0x411bb6,0x44b272,0x4171f6,0x417541,0x44b81d]:
 print("\n===== TARGET",hex(target),"=====")
 off=target-cv
 # find plausible func starts <= target among push ebp/mov ebp,esp in prior 0x1200
 lo=max(0,off-0x1800)
 cand=[]
 for i in range(lo,off):
  if code[i:i+3] in (b"\x55\x8b\xec",b"\x55\x89\xe5"): cand.append(cv+i)
 st=cand[-1] if cand else cv+lo
 print("start approximation",hex(st))
 chunk=code[st-cv:min(len(code),off+0x500)]
 for ins in md.disasm(chunk,st):
  ann=""
  if "0x" in ins.op_str:
   for token in ins.op_str.replace("["," ").replace("]"," ").replace(","," ").split():
    if token.startswith("0x"):
     try:
      v=int(token,16)
      if base<=v<base+pe.OPTIONAL_HEADER.SizeOfImage:
       try:
        oo=pe.get_offset_from_rva(v-base);e=d.find(b"\0",oo,min(len(d),oo+180));s=d[oo:e]
        if len(s)>=3 and sum(32<=x<127 for x in s)/len(s)>.8: ann=" ; "+repr(s.decode("latin1","replace"))
       except:pass
     except:pass
  print("%08X %-18s %-7s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann))
  if ins.address>off+0x180: break
