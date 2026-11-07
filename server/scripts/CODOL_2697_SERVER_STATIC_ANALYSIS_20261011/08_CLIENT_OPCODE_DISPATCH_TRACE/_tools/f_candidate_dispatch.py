
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
for f in (0xA2660,0x6D340,0x6E060,0x1B1370):
    lines.append('\n===== FUNC %#x =====' % f)
    ins=list(md.disasm(im.read_rva(f,0x800),im.ib+f))
    out=[]
    for x in ins:
        out.append(x)
        if x.mnemonic=='ret': break
    for x in out:
        rr=x.address-im.ib
        note=''
        if x.mnemonic=='jmp' and '[' in x.op_str: note=' <-- INDIRECT'
        if x.mnemonic in ('jl','jle','jg','jge','je','jne','ja','jae','jb','jbe') and any(x.op_str.endswith('0x%x'%k) for k in range(1,7)): note=' <-- cmp branch'
        lines.append('%08x %-20s %-8s %s%s' % (rr,x.bytes.hex(),x.mnemonic,x.op_str,note))
open(os.path.join(OUT,'f_candidate_dispatch_disasm.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('written ins',len(out))
