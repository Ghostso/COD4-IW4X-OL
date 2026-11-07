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
def cstr(va,n=72):
    b=read_va(va,n)
    if not b: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
b=read_va(0x082E13FC,4)
obj=struct.unpack('<I',b)[0]
print('对象 [0x82E13FC] = 0x%08X' % obj)
vt=struct.unpack('<I', read_va(obj,4))[0]
print('vtable = 0x%08X' % vt)
md=Cs(CS_ARCH_X86, CS_MODE_32)
for slot in (0x60,0x64,0xBC,0xC0,0xD0,0x3C):
    fn=struct.unpack('<I', read_va(vt+slot,4))[0]
    print()
    print('=== vtable+0x%02X -> 0x%08X ===' % (slot, fn))
    code=read_va(fn, 0x60)
    if not code: continue
    n=0
    for ins in md.disasm(code, fn):
        ann=''
        if '0x' in ins.op_str:
            for tok in ins.op_str.replace(',',' ').split():
                if tok.startswith('0x'):
                    try: va=int(tok,16)
                    except: continue
                    if 0x00C00000<=va<=0x01000000:
                        s=cstr(va)
                        if s and len(s)>=3: ann='; \"%s\"'%s
        print('   %08X  %-18s %-7s %-28s%s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, ann))
        n+=1
        if n>22: break
