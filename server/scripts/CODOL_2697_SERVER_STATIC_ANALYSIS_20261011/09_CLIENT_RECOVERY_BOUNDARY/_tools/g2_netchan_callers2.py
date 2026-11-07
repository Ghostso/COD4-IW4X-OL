
import pefile,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text');md=Cs(CS_ARCH_X86,CS_MODE_32)
def off(r):return text.PointerToRawData+(r-text.VirtualAddress)
def dis(r,n):return list(md.disasm(d[off(r):off(r)+n],ib+r))
def prevpro(r,back=0x800):
 best=None
 for x in range(max(text.VirtualAddress,r-back),r):
  if d[off(x):off(x)+3]==bytes.fromhex('558bec') and d[off(x):off(r)].find(b'\xc3')<0:best=x
 return best
out=[]
for r in (0x61B196,0x61B61E,0x61B75E,0x61B86E,0x61BB6E):
 f=prevpro(r);out.append('CALLER %#x FUNC %s' % (r,hex(f) if f else '?'))
 if f:
  for x in dis(f,0x180):
   out.append('  %08x %-18s %s' % (x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
out.append('\nHELPER 0xA04860')
for x in dis(0xA04860,0x120):out.append('%08x %-18s %s' % (x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
out.append('\nHELPER 0x9FA070')
for x in dis(0x9FA070,0x120):out.append('%08x %-18s %s' % (x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_netchan_callers2.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
