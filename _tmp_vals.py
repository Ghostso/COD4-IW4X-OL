import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
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
obj=0x3D5BB008
print('对象基址 = 0x%08X' % obj)
print()
print('=== 闸门相关字节 ===')
for off,label in ((0x283,'闸门A 条件3'),(0x10614,'★闸门B 直接返回值'),
                  (0x38710,'闸门A 条件2'),(0x105fc,'0x6311C0 读的字节'),
                  (0x20,'clientState'),(0xfe,'?'),(0x283,'?')):
    b=read_va(obj+off,1)
    v=b[0] if b else None
    print('  +0x%-8X %-22s = %s' % (off, label, v))
print()
# 闸门A 的计时器 +0x106F8 是 8 字节的 float/double
b=read_va(obj+0x106F8, 16)
print('=== 闸门A 计时器 +0x106F8 ===')
print('  bytes:', b.hex(' '))
print('  as float64:', struct.unpack('<d', b[:8])[0])
print('  as 2xfloat32:', struct.unpack('<ff', b[:8]))
print()
# +0x5C 虚函数
vt=struct.unpack('<I', read_va(obj,4))[0]
fn=struct.unpack('<I', read_va(vt+0x5C,4))[0]
print('vtable+0x5C -> 0x%08X  (闸门A 的前置)' % fn)
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86, CS_MODE_32)
code=read_va(fn,0x40)
for ins in md.disasm(code,fn):
    print('   %08X  %-18s %-7s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
