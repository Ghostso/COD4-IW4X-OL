from pathlib import Path
import pefile
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
p=ROOT/r'COD OL\codoMP_client_shipRetail.exe'; d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
# Locate all RTTI-looking names containing IsTCLS and dump nearby complete locator + vtable
needle=b'IsTCLSLogOn'
hits=[]; st=0
while True:
 i=d.find(needle,st)
 if i<0: break
 hits.append(i); st=i+1
print('hits',[hex(x) for x in hits])
def va2off(va):
 r=va-base
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):return s.PointerToRawData+r-s.VirtualAddress
 raise ValueError
def off2va(off):
 for s in pe.sections:
  if s.PointerToRawData<=off<s.PointerToRawData+s.SizeOfRawData:return base+s.VirtualAddress+off-s.PointerToRawData
 raise ValueError
for i in hits:
 print('\nHIT off',hex(i),'va',hex(off2va(i)),'ctx',d[i-128:i+256])
 print('asciictx',d[i-128:i+256].replace(b'\0',b'.')[:384])
 # find type descriptor candidates that precede in 0x100, locator candidates that reference name
 va=off2va(i)
 # scan all aligned 4byte references in rdata/data to va-16? MSVC RTTI name preceded by 0,0
 for ref in [va,va-16,va-8,va-4,va+8,va+16]:
  pat=ref.to_bytes(4,'little'); xr=[]
  for s in pe.sections:
   if not (s.Characteristics & 0x40000000): continue
   b=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]; sv=base+s.VirtualAddress; pos=0
   while True:
    q=b.find(pat,pos)
    if q<0: break
    xr.append((sv+q,sv+q-base)); pos=q+1
  if xr: print('REF',hex(ref),'->',[(hex(a),hex(r)) for a,r in xr])
