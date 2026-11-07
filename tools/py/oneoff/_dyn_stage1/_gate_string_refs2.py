from pathlib import Path
import pefile, struct
from capstone import *
ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
p=ROOT/r"COD OL\codoMP_client_shipRetail.exe"; d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
needles=[('WIN_NO_TCLS','ascii'),('WIN_NO_TCLS','utf-16le'),('IsTCLSLogOn','ascii'),('IsTCLSLogOn','utf-16le'),('请使用腾讯游戏登录器','utf-16le')]
def off2va(off):
 for s in pe.sections:
  if s.PointerToRawData<=off<s.PointerToRawData+s.SizeOfRawData:return base+s.VirtualAddress+off-s.PointerToRawData
 raise ValueError(hex(off))
def va2off(va):
 r=va-base
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):return s.PointerToRawData+r-s.VirtualAddress
 raise ValueError(hex(va))
for n,enc in needles:
 try:nb=n.encode(enc)
 except UnicodeEncodeError:continue
 st=0
 while True:
  i=d.find(nb,st)
  if i<0:break
  try: va=off2va(i)
  except Exception as e: st=i+1; continue
  print('\nHIT',repr(n),enc,'off',hex(i),'va',hex(va),'bytes',d[i:i+64].hex())
  pat=struct.pack('<I',va); xr=[]
  for s in pe.sections:
   if not (s.Characteristics & 0x20000000): continue
   b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; sv=base+s.VirtualAddress; pos=0
   while True:
    q=b.find(pat,pos)
    if q<0:break
    xr.append(sv+q); pos=q+1
  print('XREF32',[hex(x) for x in xr])
  for x in xr:
   print('CTX',hex(x))
   try:
    # from section start to x+80 is safer than arbitrary negative due long function
    lo=max(base, x-160); code=d[va2off(lo):va2off(x+80)]
    for ins in Cs(CS_ARCH_X86,CS_MODE_32).disasm(code,lo): print('%08X %-20s %s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
   except Exception as e: print('diserr',e)
  st=i+1
