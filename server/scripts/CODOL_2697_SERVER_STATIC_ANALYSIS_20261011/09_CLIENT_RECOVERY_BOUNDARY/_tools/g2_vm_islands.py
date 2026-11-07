
import pefile,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text');md=Cs(CS_ARCH_X86,CS_MODE_32)
def off(r):return text.PointerToRawData+(r-text.VirtualAddress)
def dis(r,n):return list(md.disasm(d[off(r):off(r)+n],ib+r))
out=[]
for label,start,length in [('A04800',0xA04800,0x120),('9FA000',0x9FA000,0x120),('61B000',0x61B000,0x800),('61AD00',0x61AD00,0x400)]:
 out.append('===== %s =====' % label)
 for x in dis(start,length):
  out.append('%08x %-20s %s' % (x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
 out.append('')
# exact prologues in windows
for label,start,end in [('A048',0xA04000,0xA05000),('9FA0',0x9FA000,0x9FB000),('61B',0x61B000,0x61C000)]:
 hits=[]
 for r in range(start,end-2):
  if d[off(r):off(r)+3]==bytes.fromhex('558bec'):hits.append(r)
 out.append('%s prologues=%s' % (label,repr(hits[:80])))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_vm_islands.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
