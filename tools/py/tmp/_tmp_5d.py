import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=90):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 找 0x005D34CF 所在函数入口
last=None
i=img.find(b'\x55\x8b\xec', 0x005D3000-LO, 0x005D34CF-LO)
while i>=0:
    if all(cov[i+k]==1 for k in range(3)): last=LO+i
    i=img.find(b'\x55\x8b\xec', i+1, 0x005D34CF-LO)
print('调用点所在函数入口 ≈ 0x%08X' % last if last else '未找到')
print()
if last:
    c=rd(last, 0x150)
    print('=== 0x%08X 起 ===' % last)
    for ins in md.disasm(c,last):
        ann=''
        if '0x' in ins.op_str:
            for tok in ins.op_str.replace(',',' ').split():
                if tok.startswith('0x'):
                    try: v=int(tok,16)
                    except: continue
                    if 0x00C00000<=v<=0x01100000:
                        s=cstr(v,60)
                        if s and len(s)>=3: ann='; \"%s\"'%s
        mk='  <<<' if ins.address==0x005D34CF else ''
        print('   %08X  %-18s %-7s %-28s%s%s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann,mk))
        if ins.address>=0x005D34DF: break
