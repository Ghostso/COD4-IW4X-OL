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
# 从 0x63E400 开始解, 找包含 0x63E5FD 的函数范围
c=rd(0x0063E400,0x2A0)
prev_ret=None
start=None
for ins in md.disasm(c,0x0063E400):
    if ins.mnemonic=='ret' and ins.address<0x0063E5FD:
        prev_ret=ins.address
    if ins.address>0x0063E5FD+0x20: break
print('0x63E5FD 之前的最后一个 ret = %s' % (hex(prev_ret) if prev_ret else '无'))
start_guess = (prev_ret+1) if prev_ret else 0x0063E400
# 对齐: ret 后面通常是 cc 填充, 跳过
b=rd(start_guess, 8)
print('ret 后字节:', b.hex(' ') if b else '?')
# 找 0x63E5FD 所在函数: 从 0x63E400 起逐条找序言, 取最后一个 < 0x63E5FD 的
i=img.find(b'\x55\x8b\xec', 0x0063E400-LO, 0x0063E5FD-LO)
last=None
while i>=0:
    if all(cov[i+k]==1 for k in range(3)): last=LO+i
    i=img.find(b'\x55\x8b\xec', i+1, 0x0063E5FD-LO)
print('最后一个序言 < 0x63E5FD = 0x%08X' % last if last else '无')
if last:
    c=rd(last, 0x230)
    print()
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
        mk='  <<<' if ins.address==0x0063E5FD else ''
        print('  %08X  %-20s %-7s %-28s%s%s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann,mk))
        if ins.address>0x0063E620: break
