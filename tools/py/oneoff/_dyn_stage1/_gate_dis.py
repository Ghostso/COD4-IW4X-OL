from pathlib import Path
import pefile, struct, sys, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM
root=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
exe=root/"COD OL/codoMP_client_shipRetail.exe"
d=exe.read_bytes(); pe=pefile.PE(data=d,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase; md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
terms=[b"WIN_NO_TCLS",b"IsTCLSLogOn"]
def va(off): return base+pe.get_rva_from_offset(off)
def off(v): return pe.get_offset_from_rva(v-base)
def sec(v):
 r=v-base
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData): return s.Name.rstrip(b"\0").decode("latin1")
 return "?"
for t in terms:
 print("TERM",t)
 offs=[]; p=0
 while True:
  i=d.find(t,p)
  if i<0:break
  offs.append(i);p=i+1
 print("offs",[hex(x) for x in offs],"vas",[hex(va(x)) for x in offs])
 for v in [va(x) for x in offs]:
  ptr=struct.pack("<I",v)
  p=0; refs=[]
  while True:
   i=d.find(ptr,p)
   if i<0:break
   refs.append(i);p=i+1
  print(" refs_to",hex(v),[hex(va(x)) for x in refs])
  for ro in refs:
   rv=va(ro)
   print("  REF VA",hex(rv),"sec",sec(rv))
   o=off(rv)
   lo=max(0,o-160); hi=min(len(d),o+240)
   rlo=pe.get_rva_from_offset(lo)
   for ins in md.disasm(d[lo:hi],base+rlo):
    mark=">>" if ins.address==rv else "  "
    print("   %s%08X %-20s %-7s %s"%(mark,ins.address-base,ins.bytes.hex(),ins.mnemonic,ins.op_str))
