
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text');md=Cs(CS_ARCH_X86,CS_MODE_32)
def off(r):return text.PointerToRawData+(r-text.VirtualAddress)
def dis(r,n):return list(md.disasm(d[off(r):off(r)+n],ib+r))
out=[]
for site in (0x76D65E,0x775A6E,0x784F7F,0x788135):
 out.append('===== RECV %#x =====' % site)
 for x in dis(site-0x180,0x300):
  rr=x.address-ib
  mark='>>' if rr<=site<rr+x.size else '  '
  out.append('%s %08x %-20s %s' % (mark,rr,x.bytes.hex(),x.mnemonic+' '+x.op_str))
 out.append('')
for label,start,end in [('76',0x76C000,0x770000),('77',0x774000,0x776000),('78',0x783000,0x789000)]:
 hits=[]
 for r in range(start,end-2):
  if d[off(r):off(r)+3]==bytes.fromhex('558bec'):hits.append(r)
 out.append('%s prologues=%s' % (label,repr(hits[:120])))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_game_recv.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:900]))
