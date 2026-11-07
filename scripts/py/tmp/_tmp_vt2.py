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
            return f[va-base:va-base+n], fn
    return None,None
def cstr(va,n=96):
    b,_=read_va(va,n)
    if not b: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
md=Cs(CS_ARCH_X86, CS_MODE_32)
print('=== 闸门函数 0x62FE30 的头部字节 (确认是否解壳) ===')
b,_=read_va(0x0062FE30, 0x18)
print('  ', b.hex(' '))
print()
print('=== 验证 +0x10614 的基址: 从 0x62FE80 反查 ===')
b2,_=read_va(0x0062FE80, 12)
print('  ', b2.hex(' '))
print()
print('=== vtable 0x00DC7274 前 16 槽 ===')
for k in range(0,0x40,4):
    v=struct.unpack('<I', read_va(0x00DC7274+k,4)[0])[0]
    nm=''
    if 0x400000<=v<0x0EA59000:
        # 该函数内部是否引用了已知串
        pass
    print('   +0x%02X  0x%08X' % (k,v))
print()
print('=== 该 vtable 是否在 RTTI 表里 (搜 0x00DC7274 的指针引用) ===')
pat=struct.pack('<I',0x00DC7274)
for base,size,fn in idxs:
    if not (0x00D00000<=base<0x01000000): continue
    try: dd=open(os.path.join(D,fn),'rb').read()
    except: continue
    i=dd.find(pat)
    while i>=0:
        print('   0x%08X (%s+0x%X)' % (base+i, fn, i))
        i=dd.find(pat,i+1)
