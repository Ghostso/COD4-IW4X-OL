
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
p=r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
d=open(p,'rb').read();pe=pefile.PE(data=d,fast_load=True);ib=pe.OPTIONAL_HEADER.ImageBase
s=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.rimp')
raw=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
out=[];out.append('RIMP VA=%#x VSZ=%#x RAWPTR=%#x RAWSZ=%#x'%(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData))
out.append('first 256: '+raw[:256].hex())
md=Cs(CS_ARCH_X86,CS_MODE_32)
out.append('DISASM:')
for x in md.disasm(raw[:0x400],ib+s.VirtualAddress):out.append('%08x %-20s %s'%(x.address,x.bytes.hex(),x.mnemonic+' '+x.op_str))
# find common trampoline bytes and address table structure
for pat in [b'\xff\x25',b'\xe9',b'\x68',b'\xc3']:
 out.append('PAT %s count=%d'%(pat.hex(),raw.count(pat)))
open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\09_CLIENT_RECOVERY_BOUNDARY\_data\g1_rimp.txt','w',encoding='utf-8').write('\n'.join(out))
print('\n'.join(out[:400]))
