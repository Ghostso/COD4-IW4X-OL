import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\FIXMC_20261027_140146'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 找函数入口
last=None
i=img.find(b'\x55\x8b\xec', 0x00662900-LO, 0x00662A6C-LO)
while i>=0:
    if all(cov[i+k]==1 for k in range(3)): last=LO+i
    i=img.find(b'\x55\x8b\xec', i+1, 0x00662A6C-LO)
print('函数入口 ≈ 0x%08X' % last if last else '未找到')
if last:
    c=rd(last,0x120)
    n=0
    for ins in md.disasm(c,last):
        ann=''
        if '0x' in ins.op_str:
            for tok in ins.op_str.replace(',',' ').split():
                if tok.startswith('0x'):
                    try: v=int(tok,16)
                    except: continue
                    if 0x00C00000<=v<=0x01100000:
                        s=cstr(v,60)
                        if s and len(s)>=4: ann='   ; \"%s\"'%s
        print('   %08X  %-20s %-7s %-30s%s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann))
        n+=1
        if ins.mnemonic=='ret' or n>45: break
