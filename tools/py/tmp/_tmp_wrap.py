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
print('=== 三个包装函数的完整体 ===')
for start,param in ((0x0063A720,0),(0x0063A770,1),(0x0063A7C0,2)):
    print()
    print('--- 0x%08X  (push %d) ---' % (start,param))
    c=rd(start,0x38)
    for ins in md.disasm(c,start):
        print('   %08X  %-16s %-7s %s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
        if ins.mnemonic=='ret': break
print()
print('=== 谁调用这三个包装 ===')
for tgt,name in ((0x0063A720,'type0'),(0x0063A770,'type1'),(0x0063A7C0,'type2')):
    n=0
    i=img.find(b'\xE8', 0x400000-LO, 0x0EA59000-LO)
    out=[]
    while i>=0:
        if all(cov[i+k]==1 for k in range(5)):
            rel=struct.unpack_from('<i',img,i+1)[0]
            if LO+i+5+rel==tgt: out.append(LO+i)
        i=img.find(b'\xE8',i+1,0x0EA59000-LO)
    print('  %s (0x%08X) 调用者: %s' % (name,tgt,[hex(x) for x in out] or '无'))
print()
print('=== 0x00E69CAC 是什么 ===')
b=rd(0x00E69CAC,80)
if b:
    print('  raw:', b[:48].hex(' '))
    print('  可打印:', ''.join(chr(c) if 32<=c<=126 else '.' for c in b[:64]))
