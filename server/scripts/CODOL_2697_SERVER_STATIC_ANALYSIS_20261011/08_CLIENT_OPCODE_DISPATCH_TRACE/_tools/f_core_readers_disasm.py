
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32)
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
funcs=[0x49d80,0x6d340,0x6e060,0xa1bf0,0xa2660,0xa2d90,0xa2e50,0xaa430,0xaad80,0xb4ec0,0x1ac670,0x1ac800,0x1ac850,0x1ac8a0,0x1acaa0,0x1ad3a0,0x1b1370,0x34fd80]
for f in funcs:
    lines.append('\n===== FUNC %#x =====' % f)
    # disassemble until ret or 0x400 bytes
    for ins in md.disasm(im.read_rva(f,0x500),im.ib+f):
        rr=ins.address-im.ib
        lines.append('%08x %-20s %-8s %s' % (rr,ins.bytes.hex(),ins.mnemonic,ins.op_str))
        if ins.mnemonic=='ret': break
open(os.path.join(OUT,'f_core_readers_disasm.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('written bytes',len('\n'.join(lines)))
