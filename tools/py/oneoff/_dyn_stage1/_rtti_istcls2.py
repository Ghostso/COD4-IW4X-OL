from pathlib import Path
import pefile,struct
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
p=ROOT/r'COD OL\codoMP_client_shipRetail.exe'; d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
def va2off(va):
 r=va-base
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):return s.PointerToRawData+r-s.VirtualAddress
 raise ValueError(hex(va))
def off2va(o):
 for s in pe.sections:
  if s.PointerToRawData<=o<s.PointerToRawData+s.SizeOfRawData:return base+s.VirtualAddress+o-s.PointerToRawData
 raise ValueError(hex(o))
def q(va,n=16): return struct.unpack_from('<'+'I'*n,d,va2off(va))
def refs(va):
 out=[]
 for s in pe.sections:
  if not (s.Characteristics & 0x40000000): continue
  b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; sv=base+s.VirtualAddress; pat=struct.pack('<I',va); st=0
  while True:
   qq=b.find(pat,st)
   if qq<0:break
   out.append(sv+qq); st=qq+1
 return out
for nameoff in [0x7623eb,0x7623e4]:
 va=off2va(nameoff)
 print('\nNAME',hex(va),d[nameoff-32:nameoff+80])
# expected td and nearby refs
for td in [0xE763DC,0xE763E4]:
 print('\nTD cand',hex(td),'q',tuple(hex(x) for x in q(td,4)))
 print('refs',[hex(x) for x in refs(td)])
 for r in refs(td): print(' REF CTX',hex(r),'q',tuple(hex(x) for x in q(r-16,8)))
