from pathlib import Path
import pefile, struct
from capstone import *
ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
targets=[(ROOT/r"COD OL\codoMP_client_shipRetail.exe",[0x6b2edc,0x6b2eec]),(ROOT/r"COD OL\codoMP_client_shipRetailBase.dll",[0x88ea88,0x88ea98])]
for p,offs in targets:
 d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
 print('\n=====',p.name,'base',hex(base),'=====')
 def off2va(off):
  for s in pe.sections:
   if s.PointerToRawData<=off<s.PointerToRawData+s.SizeOfRawData:return base+s.VirtualAddress+off-s.PointerToRawData
  raise ValueError('off '+hex(off))
 def va2off(va):
  r=va-base
  for s in pe.sections:
   if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):return s.PointerToRawData+r-s.VirtualAddress
  raise ValueError(hex(va))
 def dump(lo,hi):
  try: code=d[va2off(lo):va2off(hi)]
  except Exception as e: print('dumpfail',hex(lo),e); return
  for i in Cs(CS_ARCH_X86,CS_MODE_32).disasm(code,lo): print('%08X %-24s %-8s %s'%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
 for off in offs:
  va=off2va(off)
  print('STR off',hex(off),'va',hex(va),'bytes',d[off:off+80])
  pat=struct.pack('<I',va); xr=[]
  for s in pe.sections:
   if not (s.Characteristics & 0x20000000): continue
   b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; sv=base+s.VirtualAddress; pos=0
   while True:
    q=b.find(pat,pos)
    if q<0:break
    xr.append(sv+q); pos=q+1
  print('XREF',[hex(x) for x in xr])
  for x in xr:
   st=x
   for y in range(x-1,max(base,x-0x800),-1):
    try: bb=d[va2off(y):va2off(y)+3]
    except: continue
    if bb==b'\x55\x8b\xec': st=y; break
   print('FUNC',hex(st),'XREF',hex(x)); dump(st,min(0x300,x-st+0x100))
