
import pefile,struct,hashlib
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read(); pe=pefile.PE(data=d,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text')
md=Cs(CS_ARCH_X86,CS_MODE_32)
def rva_off(r): return text.PointerToRawData+(r-text.VirtualAddress)
def dis(r,n=200):
 b=d[rva_off(r):rva_off(r)+n]
 return list(md.disasm(b,ib+r))
def prev_prologue(r):
 # nearest preceding 55 8B EC with no ret in between, within 0x2000
 best=None
 for x in range(r-0x2000,r-2):
  if x<text.VirtualAddress: continue
  if d[rva_off(x):rva_off(x)+3]==bytes.fromhex('558bec'):
   # ensure no ret between x and r raw bytes approximately
   if d[rva_off(x):rva_off(r)].find(b'\xc3')<0: best=x
 return best
def callers(target_rva):
 out=[]; target=ib+target_rva
 for i in range(text.PointerToRawData, text.PointerToRawData+text.SizeOfRawData-4):
  if d[i]!=0xE8: continue
  src=ib+text.VirtualAddress+(i-text.PointerToRawData)
  rel=struct.unpack_from('<i',d,i+1)[0]
  if src+5+rel==target: out.append(text.VirtualAddress+(i-text.PointerToRawData))
 return out
sites=[0x602443,0x6029C0,0x6052AD,0x76D65E,0x775A6E,0x784F7F,0x788135]
out=[]
for s in sites:
 f=prev_prologue(s); out.append('===== RECV SITE %#x FUNC %s =====' % (s,hex(f) if f else 'UNKNOWN'))
 if f:
  out.append('callers='+repr(callers(f)))
  for x in dis(max(text.VirtualAddress,f-0x20), (s-f)+0x180 if s>=f else 0x300):
   rr=x.address-ib
   if f-0x20<=rr<=s+0x120:
    mark='>>' if rr<=s<rr+x.size else '  '
    out.append('%s %08x %-20s %-8s %s' % (mark,rr,x.bytes.hex(),x.mnemonic,x.op_str))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_recv_sites.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
