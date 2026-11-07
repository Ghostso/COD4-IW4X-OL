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
sites=[0x005D34CF,0x0063A74D,0x0063A79E,0x0063A7EE,0x0063B5AC]
for s in sites:
    print('='*70)
    print('调用点 0x%08X' % s)
    c=rd(s-0x40, 0x50)
    if c is None: print('  未覆盖'); continue
    for ins in md.disasm(c, s-0x40):
        ann=''
        if '0x' in ins.op_str:
            for tok in ins.op_str.replace(',',' ').split():
                if tok.startswith('0x'):
                    try: v=int(tok,16)
                    except: continue
                    if 0x00C00000<=v<=0x01100000:
                        st=cstr(v,60)
                        if st and len(st)>=3: ann='; \"%s\"'%st
        mk='  <<< call 0x63E510' if ins.address==s else ''
        print('   %08X  %-18s %-7s %-28s%s%s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann,mk))
        if ins.address>=s: break
