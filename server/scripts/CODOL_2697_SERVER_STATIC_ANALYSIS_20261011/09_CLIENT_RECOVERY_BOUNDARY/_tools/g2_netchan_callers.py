
import pefile,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text');md=Cs(CS_ARCH_X86,CS_MODE_32)
def off(r):return text.PointerToRawData+(r-text.VirtualAddress)
def scan_calls(t):
 out=[];tva=ib+t
 for i in range(text.PointerToRawData,text.PointerToRawData+text.SizeOfRawData-4):
  if d[i]!=0xe8:continue
  rel=struct.unpack_from('<i',d,i+1)[0]
  src=ib+text.VirtualAddress+(i-text.PointerToRawData)
  if src+5+rel==tva:out.append(text.VirtualAddress+(i-text.PointerToRawData))
 return out
def dis(r,n):return list(md.disasm(d[off(r):off(r)+n],ib+r))
out=[]
targets=[0x602430,0x6029a0,0x605280,0x76D630,0x775A00,0x784F00,0x788000,0x61ADF1]
for t in targets:
 out.append('TARGET %#x CALLS %s' % (t,repr(scan_calls(t))))
# find containing function for 0x61adf1 by backward prologue
r=0x61ADF1;best=None
for x in range(r-0x800,r):
 if x<text.VirtualAddress:continue
 if d[off(x):off(x)+3]==bytes.fromhex('558bec'):best=x
out.append('FUNC_FOR_61ADF1 %s' % (hex(best) if best else '?'))
if best:
 for x in dis(best,0x400):
  out.append('%08x %-18s %s' % (x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
  if x.mnemonic=='ret' and x.address-ib>r: break
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_netchan_callers.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:500]))
