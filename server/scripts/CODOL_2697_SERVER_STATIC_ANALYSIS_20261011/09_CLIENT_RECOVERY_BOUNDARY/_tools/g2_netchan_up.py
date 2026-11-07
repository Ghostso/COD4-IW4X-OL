
import pefile,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text');md=Cs(CS_ARCH_X86,CS_MODE_32)
def off(r):return text.PointerToRawData+(r-text.VirtualAddress)
def callers(t):
 out=[];tva=ib+t
 for i in range(text.PointerToRawData,text.PointerToRawData+text.SizeOfRawData-4):
  if d[i]!=0xe8:continue
  src=ib+text.VirtualAddress+(i-text.PointerToRawData);rel=struct.unpack_from('<i',d,i+1)[0]
  if src+5+rel==tva:out.append(text.VirtualAddress+i-text.PointerToRawData)
 return out
def dis(r,n):return list(md.disasm(d[off(r):off(r)+n],ib+r))
out=[]
for t in (0x61ADA0,0xA04860,0x9FA070,0x602430):
 out.append('TARGET %#x CALLERS %s' % (t,repr(callers(t))))
out.append('\n===== DISASM 0x61ADA0 =====')
for x in dis(0x61ADA0,0x180):
 out.append('%08x %-18s %s' % (x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_netchan_up.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
