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
print('=== [0x00DC7270] = 0x00DF96D8 是什么 ===')
b=rd(0x00DF96D8,4)
if b: print('  -> 0x%08X' % struct.unpack('<I',b)[0])
b=rd(0x00DF96D0,24)
if b:
    print('  0x00DF96D0 起:', b.hex(' '))
md=Cs(CS_ARCH_X86, CS_MODE_32)
print()
print('=== 构造函数 0x0062C010 前后 ===')
c=rd(0x0062C000,0x60)
for ins in md.disasm(c,0x0062C000):
    ann=''
    if '0x' in ins.op_str:
        for tok in ins.op_str.replace(',',' ').split():
            if tok.startswith('0x'):
                try: v=int(tok,16)
                except: continue
                if 0x00C00000<=v<=0x01100000:
                    s=cstr(v,60)
                    if s and len(s)>=3: ann='; \"%s\"'%s
    mk='  <<<' if ins.address==0x0062C025 else ''
    print('  %08X  %-20s %-7s %-30s%s%s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann,mk))
