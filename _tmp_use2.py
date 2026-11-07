import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
def read_va(va,n):
    for base,size,fn in idxs:
        if base <= va < base+size:
            f=open(os.path.join(D,fn),'rb').read()
            return f[va-base:va-base+n]
    return None
def cstr(va,n=64):
    b=read_va(va,n)
    if not b: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
md=Cs(CS_ARCH_X86, CS_MODE_32)
print('=== dw_autoStartGame 唯一真实读取点: 0x0063C940 前后 ===')
code = read_va(0x0063C900, 0x100)
for ins in md.disasm(code, 0x0063C900):
    ann=''
    if '0x' in ins.op_str:
        for tok in ins.op_str.replace(',',' ').split():
            if tok.startswith('0x'):
                try: va=int(tok,16)
                except: continue
                if 0x00C00000<=va<=0x01000000:
                    s=cstr(va)
                    if s and len(s)>=4: ann='; "%s"'%s
    mark = '  <<<' if ins.address in (0x0063C972,) else ''
    print('  %08X  %-22s %-7s %-32s%s%s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, ann, mark))
