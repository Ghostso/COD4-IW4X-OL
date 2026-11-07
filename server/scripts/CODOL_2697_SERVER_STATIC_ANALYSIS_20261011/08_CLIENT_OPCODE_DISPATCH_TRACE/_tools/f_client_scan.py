import sys, os, struct, json, hashlib
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32)
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
os.makedirs(OUT,exist_ok=True)

def rva_to_file(im,rva):
    s=im.sec_of(rva)
    if not s: return None
    nm,va,vsz,ptr,rsz=s
    return ptr+(rva-va)

def va_refs(im,va):
    res=[]; b=struct.pack('<I',va)
    for nm,va0,vsz,ptr,rsz in im.sections:
        if rsz==0: continue
        i=ptr
        while True:
            j=im.data.find(b,i,ptr+rsz)
            if j<0: break
            res.append((nm,va0+(j-ptr),j)); i=j+1
    return res

def rel_refs(im,target_va):
    res=[]
    for nm,va0,vsz,ptr,rsz in im.sections:
        if rsz<5 or nm not in ('.text','.tvm0','.rimp'): continue
        d=im.data
        for i in range(ptr,ptr+rsz-4):
            op=d[i]
            if op not in (0xE8,0xE9): continue
            rel=struct.unpack_from('<i',d,i+1)[0]
            src_va=im.ib+va0+(i-ptr)
            tgt=src_va+5+rel
            if tgt==target_va:
                res.append((nm,va0+(i-ptr),i,op,src_va,tgt))
    return res

def disasm(im,rva,count=40):
    out=[]
    for ins in md.disasm(im.read_rva(rva,count*15),im.ib+rva):
        out.append(ins)
        if len(out)>=count: break
    return out

def ctx(im,rva,n=18):
    return ' | '.join(f'{x.address:08x} {x.mnemonic} {x.op_str}' for x in disasm(im,max(0,rva-8),n))

im=c.load()
print('image',im.path)
print('sha256',hashlib.sha256(im.data).hexdigest())
print('imagebase',hex(im.ib))
for nm,va,vsz,ptr,rsz in im.sections:
    print(f'section {nm} rva={va:#x} vsz={vsz:#x} ptr={ptr:#x} rsz={rsz:#x}')

lines=[]
for target_rva,target_name in [(0xA2E50,'A2E50'),(0xA2D90,'A2D90'),(0x1AC1D0,'READ_CORE_1AC1D0'),(0x1ACB00,'COPY_CORE_1ACB00')]:
    va=im.ib+target_rva
    lines.append(f'\n===== TARGET {target_name} RVA {target_rva:#x} VA {va:#x} FILE {rva_to_file(im,target_rva):#x} =====')
    lines.append('--- first 90 instructions ---')
    for x in disasm(im,target_rva,90):
        lines.append(f'{x.address:08x} {x.address-im.ib:08x}  {x.bytes.hex():<20} {x.mnemonic:<8} {x.op_str}')
    lines.append('--- absolute VA refs ---')
    refs=va_refs(im,va)
    if not refs: lines.append('NONE')
    for nm,rva,fo in refs:
        lines.append(f'{nm} rva={rva:#x} file={fo:#x} ctx={ctx(im,rva,18)}')
    lines.append('--- E8/E9 rel refs ---')
    rr=rel_refs(im,va)
    if not rr: lines.append('NONE')
    for nm,rva,fo,op,src,tgt in rr:
        lines.append(f'{nm} op={op:#x} site_rva={rva:#x} file={fo:#x} src_va={src:#x} target={tgt:#x} ctx={ctx(im,rva,18)}')

lines.append('\n===== CLIENT_OPCODE_CANDIDATES =====')
for pat in [b'\x83\xf8\x02',b'\x83\xf9\x02',b'\x83\xfa\x02',b'\x3c\x02',b'\x80\x3e\x02',b'\x66\x83\xf8\x02',b'\x81\xf8\x02\x00\x00\x00']:
    start=0
    while True:
        j=im.data.find(pat,start)
        if j<0: break
        rva=None; nm=None
        for sn,va,vsz,ptr,rsz in im.sections:
            if rsz and ptr<=j<ptr+rsz:
                nm=sn; rva=va+(j-ptr); break
        if rva is not None and (0x1000<=rva<0x800000 or 0x0D900000<=rva<0x0DC00000):
            lines.append(f'pattern={pat.hex()} section={nm} rva={rva:#x} file={j:#x} ctx={ctx(im,rva,18)}')
        start=j+1

open(os.path.join(OUT,'f_target_scan.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:150]))