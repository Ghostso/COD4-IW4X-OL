
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32)
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
lines=[]
lines.append('SHA256 ' + __import__('hashlib').sha256(im.data).hexdigest())
lines.append('ImageBase %#x' % im.ib)
for nm,va,vsz,ptr,rsz in im.sections:
    lines.append('SECTION %s rva=%#x vsz=%#x ptr=%#x rsz=%#x' % (nm,va,vsz,ptr,rsz))

def find_e8(target_rva, sec_filter=None):
    target_va=im.ib+target_rva; hits=[]
    for nm,va,vsz,ptr,rsz in im.sections:
        if sec_filter and nm not in sec_filter: continue
        for off in range(ptr,ptr+rsz-4):
            if im.data[off]!=0xE8: continue
            rel=struct.unpack_from('<i',im.data,off+1)[0]
            src=im.ib+va+(off-ptr)
            if src+5+rel==target_va: hits.append((nm,va+(off-ptr),off,src))
    return hits

def find_abs(target_rva):
    b=struct.pack('<I',im.ib+target_rva); res=[]; st=0
    while True:
        j=im.data.find(b,st)
        if j<0: break
        for nm,va,vsz,ptr,rsz in im.sections:
            if rsz and ptr<=j<ptr+rsz: res.append((nm,va+j-ptr,j)); break
        st=j+1
    return res

for rva,name in [(0xA2E50,'A2E50'),(0xA2D90,'A2D90'),(0x1AC1D0,'CORE_READ'),(0x1ACB00,'CORE_COPY')]:
    lines.append('\nTARGET %s RVA %#x' % (name,rva))
    lines.append('E8_E9_ALL ' + repr(find_e8(rva, {'.text','.tvm0','.rimp'})))
    lines.append('ABS ' + repr(find_abs(rva)))

# msg-like object field compares in .text
out=[]
for i in md.disasm(im.read_rva(0x1000,0x7ac90b),0x401000):
    s=i.op_str
    if i.mnemonic in ('mov','movzx') and '+ 0x1c]' in s:
        out.append('%08x %s %s' % (i.address-im.ib,i.mnemonic,s))
    if i.mnemonic=='cmp':
        for k in range(1,7):
            if s.endswith('0x%x'%k) or s.endswith('%#x'%k):
                out.append('CMP %08x %s %s' % (i.address-im.ib,i.mnemonic,s))
lines.append('\nMSG_FIELD_SCAN count=%d' % len(out))
lines.extend(out)
open(os.path.join(OUT,'f_scan_core.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:400]))
