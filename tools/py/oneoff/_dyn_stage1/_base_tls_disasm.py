from pathlib import Path
import pefile, struct
from capstone import *
from capstone.x86 import *
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL'); out=root/r'_dyn_stage1\base_tls_disasm.txt'
p=root/r'COD OL\codoMP_client_shipRetailBase.dll'; pe=pefile.PE(str(p),fast_load=True); data=p.read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
sec=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.tls')
blob=sec.get_data(); va=base+sec.VirtualAddress
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
with out.open('w',encoding='utf-8') as f:
 f.write(f'.tls raw={len(blob)} va={va:08X} vsize={sec.Misc_VirtualSize:X}\n')
 n=0
 for ins in md.disasm(blob[:0x4000],va):
  n+=1
  if ins.mnemonic in ('jmp','call','ret','retn','push','mov','lea','cmp','test') or n<80:
   f.write(f'{ins.address:08X} {ins.bytes.hex():<24} {ins.mnemonic:<8} {ins.op_str}\n')
 print(out,n)
