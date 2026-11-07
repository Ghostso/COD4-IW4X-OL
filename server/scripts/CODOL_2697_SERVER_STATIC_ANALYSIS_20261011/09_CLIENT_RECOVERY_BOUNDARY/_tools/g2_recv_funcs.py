
import pefile,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read(); pe=pefile.PE(data=d,fast_load=True); ib=pe.OPTIONAL_HEADER.ImageBase
text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text'); md=Cs(CS_ARCH_X86,CS_MODE_32)
def off(r):return text.PointerToRawData+(r-text.VirtualAddress)
def dis(r,n):return list(md.disasm(d[off(r):off(r)+n],ib+r))
def callers(t):
 out=[]; tva=ib+t
 for i in range(text.PointerToRawData,text.PointerToRawData+text.SizeOfRawData-4):
  if d[i]!=0xE8:continue
  src=ib+text.VirtualAddress+(i-text.PointerToRawData);rel=struct.unpack_from('<i',d,i+1)[0]
  if src+5+rel==tva:out.append(text.VirtualAddress+i-text.PointerToRawData)
 return out
def prevpro(r):
 for x in range(r-0x400,r-2):
  if x<text.VirtualAddress:continue
  if d[off(x):off(x)+3]==bytes.fromhex('558bec') and d[off(x):off(r)].find(b'\xc3')<0:best=x
 return best if 'best' in locals() else None
out=[]
for rva in (0x602430,0x6029C0,0x6052AD,0x76D65E,0x775A6E,0x784F7F,0x788135):
 f=prevpro(rva)
 out.append('SITE %#x FUNC %s CALLERS %s' % (rva,hex(f) if f else '?',repr(callers(f) if f else [])))
 if f:
  for x in dis(f,0x180):
   out.append('  %08x %-18s %s' % (x.address-ib,x.bytes.hex(),x.mnemonic+' '+x.op_str))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_recv_funcs.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
