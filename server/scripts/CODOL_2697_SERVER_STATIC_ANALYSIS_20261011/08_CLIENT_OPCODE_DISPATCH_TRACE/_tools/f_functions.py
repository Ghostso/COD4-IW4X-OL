import sys, os, struct, hashlib
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32)
OUT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data"

def rva_file(im,rva):
    s=im.sec_of(rva)
    if not s: return None
    nm,va,vsz,ptr,rsz=s
    return ptr+rva-va

def dis_from(im,rva,maxbytes=4096):
    code=im.read_rva(rva,maxbytes)
    out=[]
    for x in md.disasm(code,im.ib+rva):
        out.append(x)
        if x.mnemonic=='ret' or x.mnemonic.startswith('ret'):
            break
        if x.mnemonic=='jmp' and '0x' in x.op_str:
            break
    return out

def calls_and_consts(im,rva):
    out=[]
    for x in dis_from(im,rva,8192):
        rr=x.address-im.ib
        target=''
        if x.mnemonic in ('call','jmp'):
            try: target=hex(int(x.op_str,16))
            except: pass
        out.append((rr,x.bytes.hex(),x.mnemonic,x.op_str,target))
    return out

im=c.load()
lines=[]
for label,rva in [('A2E50',0xA2E50),('A2D90',0xA2D90),('READ_CORE',0x1AC1D0),('COPY_CORE',0x1ACB00),('DISPATCH_SEARCH',0xA2E00)]:
    lines.append('===== %s RVA %#x FILE %#x =====' % (label,rva,rva_file(im,rva) or 0))
    for rr,b,mn,op,tgt in calls_and_consts(im,rva):
        mark='>>' if rr==rva else '  '
        lines.append('%s %08x %-20s %-8s %s' % (mark,rr,b,mn,op))
    lines.append('')
open(os.path.join(OUT,'f_function_boundaries.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:180]))
