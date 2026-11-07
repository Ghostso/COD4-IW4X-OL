
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32)
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
# indirect jump/call patterns and jump-table base loads in .text
for ins in md.disasm(im.read_rva(0x1000,0x7ac90b),0x401000):
    s=ins.op_str; m=ins.mnemonic; rr=ins.address-im.ib
    if m in ('jmp','call') and '[' in s and ('*4' in s or '*8' in s or '+ eax' in s or '+ ecx' in s or '+ edx' in s):
        lines.append('IND %08x %-20s %-5s %s' % (rr,ins.bytes.hex(),m,s))
    if m=='mov' and '[' in s and ('*4' in s or '*8' in s) and ('0x' in s):
        lines.append('TBL %08x %-20s %-5s %s' % (rr,ins.bytes.hex(),m,s))
open(os.path.join(OUT,'f_indirect_jumps.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('count',len(lines))
print('\n'.join(lines[:120]))
