import sys, os, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32)
OUT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data"

def ft(im,rva):
    s=im.sec_of(rva)
    if not s:
        return None
    nm,va,vsz,ptr,rsz=s
    return ptr+rva-va

def dump(im,rva,back=80,fwd=220):
    s=im.sec_of(rva)
    if not s:
        return None,None,[]
    nm,va,vsz,ptr,rsz=s
    st=max(va,rva-back)
    en=min(va+rsz,rva+fwd)
    code=im.data[ptr+(st-va):ptr+(en-va)]
    return nm,st,list(md.disasm(code,im.ib+st))

def words(im,rva,n=64):
    b=im.read_rva(rva,n*4)
    if not b:
        return []
    return [struct.unpack_from('<I',b,i)[0] for i in range(0,len(b)-3,4)]

im=c.load()
lines=[]
for label,rva in [('A2E50_PTR_REGION',0xA2E50),('A2D90_PTR_REGION',0xA2D90),('TVM_CALL',0xD9D940F)]:
    lines.append('===== %s RVA %#x FILE %#x =====' % (label,rva,ft(im,rva) or 0))
    nm,st,ins=dump(im,rva,96,320)
    lines.append('section=%s disasm_start=%#x' % (nm,st or 0))
    for x in ins:
        rr=x.address-im.ib
        mark='>>' if rr<=rva<rr+x.size else '  '
        lines.append('%s %08x %08x %-20s %-8s %s' % (mark,x.address,rr,x.bytes.hex(),x.mnemonic,x.op_str))
    lines.append('--- dwords ---')
    for i,w in enumerate(words(im,rva,80)):
        lines.append('+%04x %08x' % (i*4,w))

lines.append('===== POINTER-LIKE DWORD SCAN =====')
for rva in [0x1A89500,0x1A89508,0x1A8950C,0xD16DF0,0xD16DF8,0xD16E00,0xCB83A0,0xCB83E0]:
    fo=ft(im,rva)
    if fo is None:
        continue
    lines.append('--- around %#x file=%#x ---' % (rva,fo))
    for i,w in enumerate(words(im,rva,32)):
        if 0x400000<=w<0xE000000 or 0x10000000<=w<0x20000000:
            lines.append('+%04x %08x' % (i*4,w))

lines.append('===== PROLOGUE SCAN =====')
needle=bytes.fromhex('558bec81ec')
for i in range(0,len(im.data)-8):
    if im.data[i:i+4]==needle:
        rva=None
        for nm,va,vsz,ptr,rsz in im.sections:
            if rsz and ptr<=i<ptr+rsz:
                rva=va+i-ptr
                sec=nm
                break
        if rva is not None and 0xa0000<=rva<0xa4000:
            lines.append('%s rva=%#x file=%#x' % (sec,rva,i))
open(os.path.join(OUT,'f_hit_validation.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:360]))
