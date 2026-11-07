
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32)
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
# dump helper readers 0x5ac670, 0x5ac980, 0x44c8c0
for f in (0x5ac670,0x5ac980,0x44c8c0,0x5acb00,0x5ac1d0,0x631ce0):
    lines.append('\n===== HELPER %#x =====' % f)
    for x in md.disasm(im.read_rva(f,0x400),im.ib+f):
        lines.append('%08x %-20s %-8s %s' % (x.address-im.ib,x.bytes.hex(),x.mnemonic,x.op_str))
        if x.mnemonic=='ret': break
# search all cmp reg, imm 1..6 in text; classify preceding read of [esi+0x1c] / [reg+0x1c]
lines.append('\n===== CMP 1..6 CANDIDATES =====')
for x in md.disasm(im.read_rva(0x1000,0x7ac90b),0x401000):
    if x.mnemonic!='cmp': continue
    ok=False
    for k in range(1,7):
        if x.op_str.endswith('0x%x'%k) or x.op_str.endswith('%#x'%k): ok=True
    if not ok: continue
    rr=x.address-im.ib
    lines.append('%08x %-20s %s' % (rr,x.bytes.hex(),x.op_str))
open(os.path.join(OUT,'f_helpers_and_cmp.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:250]))
