import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def u32(va):
    b=rd(va,4); return struct.unpack('<I',b)[0] if b and len(b)==4 else None
def f32(va):
    b=rd(va,4); return struct.unpack('<f',b)[0] if b and len(b)==4 else None
def cstr(va,n=110):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
U=0x3ACA0CD8
print('=== 判据使用的 dvar [0x849B7C8] ===')
h=u32(0x0849B7C8)
print('  句柄 = %s' % (('0x%08X'%h) if h else '?'))
if h:
    nm=cstr(u32(h),80)
    print('  dvar 名 = %s' % nm)
    print('  type = 0x%X  值 = %s (float %.3f)' % (u32(h+8) or 0, ('0x%08X'%u32(h+0xC)), f32(h+0xC)))
print()
print('=== 对象里判据读的两个字段 ===')
print('  +0x138 (计时器对象起始) = 0x%08X' % (u32(U+0x138) or 0))
print('  +0x140 (fadd 的偏移)   = %.6f' % (f32(U+0x140) or 0))
print('  +0x138..0x148 raw:')
b=rd(U+0x138,16)
if b: print('     ', b.hex(' '))
print()
print('=== 对比 dw_enterGameNextMapCountingDown 的注册默认值 ===')
print('  注册时: push 0x42340000 =', struct.unpack('<f', struct.pack('<I',0x42340000))[0])
print()
print('=== 该对象的完整状态 ===')
print('  +0x20 状态 = %d' % (u32(U+0x20) or 0))
for off in (0x24,0x28,0x2C,0x30,0x34,0x138,0x13C,0x140,0x144):
    v=u32(U+off)
    print('  +0x%03X = %s' % (off, ('0x%08X'%v) if v is not None else '未覆盖'))
