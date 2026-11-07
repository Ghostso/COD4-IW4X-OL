
import sys, os, struct, re
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32)
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
funcs=[0x49d80,0x6d340,0x6e060,0xa1bf0,0xa2660,0xa2d90,0xa2e50,0xaa430,0xaad80,0xb4ec0,0x1ac670,0x1ac800,0x1ac850,0x1ac8a0,0x1acaa0,0x1ad3a0,0x1b1370,0x34fd80]
lines=[]
for f in funcs:
    ins=list(md.disasm(im.read_rva(f,0x500),im.ib+f))
    # trim at first ret
    out=[]
    for x in ins:
        out.append(x)
        if x.mnemonic=='ret': break
    lines.append('\n===== FUNC %#x ins=%d =====' % (f,len(out)))
    for x in out:
        rr=x.address-im.ib
        lines.append('%08x %-20s %-8s %s' % (rr,x.bytes.hex(),x.mnemonic,x.op_str))
open(os.path.join(OUT,'f_core_readers_trim.txt'),'w',encoding='utf-8').write('\n'.join(lines))
# summary of interesting ops
summ=[]
for f in funcs:
    out=[]
    for x in md.disasm(im.read_rva(f,0x500),im.ib+f):
        out.append(x)
        if x.mnemonic=='ret': break
    hits=[x for x in out if x.mnemonic=='cmp' and any(x.op_str.endswith('0x%x'%k) for k in range(0,8)) and len(x.op_str)<30]
    calls=[x.op_str for x in out if x.mnemonic=='call']
    push_imm=[x for x in out if x.mnemonic=='push' and x.op_str.startswith('0x') and x.op_str in ('0x1','0x2','0x3','0x4','0x5','0x6')]
    summ.append('FUNC %#x cmp=[%s] pushImm=[%s] firstcalls=%s' % (f, ','.join(x.mnemonic+' '+x.op_str for x in hits), ','.join(x.op_str for x in push_imm), ' | '.join(calls[:6])))
open(os.path.join(OUT,'f_core_readers_summary.txt'),'w',encoding='utf-8').write('\n'.join(summ))
print('\n'.join(summ))
