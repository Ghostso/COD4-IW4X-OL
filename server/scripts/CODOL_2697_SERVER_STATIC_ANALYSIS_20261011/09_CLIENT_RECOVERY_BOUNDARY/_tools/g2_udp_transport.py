
import pefile,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text');md=Cs(CS_ARCH_X86,CS_MODE_32)
def off(r):return text.PointerToRawData+(r-text.VirtualAddress)
def dis(r,n):return list(md.disasm(d[off(r):off(r)+n],ib+r))
def callers(t):
 out=[];tva=ib+t
 for i in range(text.PointerToRawData,text.PointerToRawData+text.SizeOfRawData-4):
  if d[i]!=0xe8:continue
  src=ib+text.VirtualAddress+(i-text.PointerToRawData);rel=struct.unpack_from('<i',d,i+1)[0]
  if src+5+rel==tva:out.append(text.VirtualAddress+i-text.PointerToRawData)
 return out
out=[]
# print prologues in region
pros=[]
for r in range(0x775700,0x775e00):
 if d[off(r):off(r)+3]==bytes.fromhex('558bec'):pros.append(r)
out.append('PROLOGUES '+repr([hex(x) for x in pros]))
for r in pros:
 out.append('\n===== FUNC %#x CALLERS %s =====' % (r,repr(callers(r))))
 for x in dis(r,0x180):
  out.append('%08x %-18s %s' % (x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
  if x.mnemonic=='ret' and x.address-ib>r+0x20:break
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_udp_transport.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:1200]))
