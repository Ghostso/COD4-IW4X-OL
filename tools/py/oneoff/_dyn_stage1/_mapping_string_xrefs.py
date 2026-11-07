from pathlib import Path
import pefile, struct
from capstone import *
ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
for rel in [r"COD OL\TenProxy.dll", r"COD OL\codoMP_client_shipRetailBase.dll", r"COD OL\TCLS\ClientBase.dll"]:
 p=ROOT/rel; d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
 print("\n=====",rel,"base",hex(base),"=====")
 def off2va(off):
  for s in pe.sections:
   if s.PointerToRawData <= off < s.PointerToRawData+s.SizeOfRawData:
    return base+s.VirtualAddress+(off-s.PointerToRawData)
 def va2off(va):
  r=va-base
  for s in pe.sections:
   if s.VirtualAddress <= r < s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
    return s.PointerToRawData+r-s.VirtualAddress
 def dump(va,n,c=16):
  print("DIS",hex(va),hex(va+n))
  for i in Cs(CS_ARCH_X86,CS_MODE_32).disasm(d[va2off(va):va2off(va)+n],va):
   b=i.bytes
   print("%08X %-24s %-8s %s"%(i.address,b.hex(),i.mnemonic,i.op_str))
 # print strings windows
 needle="TCLS_SHAREDMEMEMORY".encode("utf-16le")
 off=0
 while True:
  off=d.find(needle,off)
  if off<0: break
  va=off2va(off)
  print("STR",hex(off),hex(va),"context",d[max(0,off-64):off+192].hex())
  # xrefs any 4 byte VA in executable sections
  pat=struct.pack('<I',va)
  xr=[]
  for s in pe.sections:
   if not (s.Characteristics & 0x20000000): continue
   b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; sv=base+s.VirtualAddress
   pos=0
   while True:
    q=b.find(pat,pos)
    if q<0: break
    xr.append(sv+q); pos=q+1
  print("XREF32",[hex(x) for x in xr])
  for x in xr:
   try: dump(max(base,x-96),192)
   except Exception as e: print("dis err",e)
  off+=1
