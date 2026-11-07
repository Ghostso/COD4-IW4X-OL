
import pefile,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
secs=[(s.Name.rstrip(b'\0').decode('latin1'),s.VirtualAddress,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
md=Cs(CS_ARCH_X86,CS_MODE_32)
def rva_of(off):
 for nm,va,ptr,rsz in secs:
  if ptr<=off<ptr+rsz:return nm,va+off-ptr
 return None,None
def off_of(r):
 for nm,va,ptr,rsz in secs:
  if va<=r<va+rsz:return ptr+r-va
 return None
terms=[b'TenProxy',b'IIPS',b'iips',b'IFS']
out=[]
for term in terms:
 st=0
 while True:
  j=d.find(term,st)
  if j<0:break
  nm,rr=rva_of(j)
  if rr is not None:
   va=ib+rr;refs=[];pat=struct.pack('<I',va);k=0
   while True:
    q=d.find(pat,k)
    if q<0:break
    sn,sr=rva_of(q);refs.append((sn,sr,q));k=q+1
   out.append('TERM %r file=%#x rva=%#x refs=%r' % (term,j,rr,refs))
   for sn,sr,q in refs:
    if sr is None:continue
    out.append('  CONTEXT %s:%#x' % (sn,sr))
    start=max(0,sr-24)
    for x in md.disasm(d[off_of(start):off_of(sr)+40],ib+start):
     mark='>>' if x.address-ib==sr else '  '
     out.append('   %s %08x %-18s %s' % (mark,x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
  st=j+1
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_platform_xrefs.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:900]))
