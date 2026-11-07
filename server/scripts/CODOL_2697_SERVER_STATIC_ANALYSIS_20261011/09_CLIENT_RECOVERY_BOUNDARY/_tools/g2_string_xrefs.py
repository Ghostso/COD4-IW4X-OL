
import pefile,struct,re
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
def dis(r,n):return list(md.disasm(d[off_of(r):off_of(r)+n],ib+r))
def find(term):return [(j,*rva_of(j)) for j in range(len(d)) if d.startswith(term.encode(),j)]
terms=['Bogus message code %d','gamestateupdate %d','gamestateupdate','EXE_CONFIGSTRINGMISMATCH','UNEXPECTED_EOF','ServerCommand','serverCommand','NetEchoProbe']
out=[]
for term in terms:
 hits=find(term)
 out.append('TERM %r hits=%s' % (term,[(hex(j),nm,hex(r) if r is not None else None) for j,nm,r in hits]))
 for j,nm,r in hits:
  if r is None:continue
  va=ib+r; refs=[]; pat=struct.pack('<I',va); st=0
  while True:
   k=d.find(pat,st)
   if k<0:break
   sn,sr=rva_of(k);refs.append((sn,sr,k));st=k+1
  out.append('  REFS %s' % [(nm,hex(rr) if rr is not None else None,hex(k)) for nm,rr,k in refs])
  for sn,rr,k in refs:
   if rr is None:continue
   out.append('  CONTEXT around %#x' % rr)
   start=max(0,rr-40)
   for x in md.disasm(d[off_of(start):off_of(rr)+48],ib+start):
    mark='>>' if x.address-ib==rr else '  '
    out.append('   %s %08x %-18s %s' % (mark,x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_string_xrefs.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:1000]))
