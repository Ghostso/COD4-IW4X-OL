
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
vt_rva=0x89856C; vt_va=ib+vt_rva; b=struct.pack('<I',vt_va);st=0;out=[]
while True:
 j=d.find(b,st)
 if j<0:break
 nm,rr=rva_of(j);out.append('VTREF sec=%s rva=%#x file=%#x' % (nm,rr,j));st=j+1
print('\n'.join(out))
# context around each ref
for line in out:
 rr=int(line.split('rva=')[1].split()[0],16)
 start=max(0,rr-48)
 print('--- context %#x ---'%rr)
 for x in md.disasm(d[off_of(start):off_of(rr)+48],ib+start):
  mark='>>' if x.address==ib+rr else '  '
  print('%s %08x %-18s %s' % (mark,x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
