
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32)
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
# inspect .tvm0 hits
for rva in (0xD9D940F,0xD97BF7E):
    nm,va,vsz,ptr,rsz=im.sec_of(rva)
    lines.append('TVM_HIT rva=%#x sec=%s file=%#x' % (rva,nm,ptr+rva-va))
    for x in md.disasm(im.read_rva(rva-32,128),im.ib+rva-32):
        lines.append('  %08x %-20s %s' % (x.address,x.bytes.hex(),x.mnemonic+' '+x.op_str))
# group .text callers of CORE_READ by containing function prologue
target=0x1ac1d0
calls=[]
for off in range(0x400,0x400+0x7aca00-5):
    if im.data[off]!=0xE8: continue
    rel=struct.unpack_from('<i',im.data,off+1)[0]
    src=0x401000+(off-0x400)
    if src+5+rel==0x400000+target: calls.append(src-0x400000)
def find_prologue(rva):
    for j in range(rva, max(0,rva-0x1000), -1):
        b=im.read_rva(j,3)
        if b==bytes.fromhex('558bec') or b==bytes.fromhex('558bff'):
            return j
    return None
groups={}
for c in calls: groups.setdefault(find_prologue(c),[]).append(c)
lines.append('CORE_READ_CALLER_FUNCS %d' % len(groups))
for f,cs in sorted(groups.items(), key=lambda x: (x[0] is None, x[0] or 0)):
    lines.append('FUNC %s calls=%s' % (hex(f) if f is not None else 'UNKNOWN', [hex(x) for x in cs]))
open(os.path.join(OUT,'f_tvm_and_callers.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines))
