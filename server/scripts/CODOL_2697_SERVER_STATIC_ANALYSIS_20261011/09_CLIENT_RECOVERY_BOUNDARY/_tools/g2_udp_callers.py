
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
out=[]
# validate actual IAT call instructions
for rva in (0x602443,0x6029c0,0x6052ad,0x76d65e,0x775a6e,0x784f7f,0x788135,0x775ade,0x775aa2,0x77592c,0x77587e):
 win_start=rva-8; code=d[off(win_start):off(rva)+12]
 ins=list(md.disasm(code,ib+win_start)); actual=[(x.address-ib,x.mnemonic,x.op_str,x.bytes.hex()) for x in ins if x.address-ib<=rva<x.address-ib+x.size]
 out.append('IATCHECK %#x actual=%s' % (rva,repr(actual)))
for f in (0x775870,0x7758b0,0x775900,0x775940,0x775a00,0x775a50,0x775a80,0x775ab0,0x775af0,0x775b30,0x775b70,0x775bb0):
 out.append('FUNC %#x CALLERS %s' % (f,repr(callers(f))))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g2_udp_callers.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out))
