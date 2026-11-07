import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
print('=== 基类 vtable 0x00DC795C 完整 (0x63C5E0 在 +0x68) ===')
for off in range(0,0xA0,4):
    b=rd(0x00DC795C+off,4)
    if b is None: print('  +0x%03X 未覆盖'%off); continue
    v=struct.unpack('<I',b)[0]
    tag='  ★ 0x63C5E0' if v==0x0063C5E0 else ''
    print('  +0x%03X  %08X%s' % (off, v, tag))
print()
print('=== 关键: 单例对象的 vtable 是哪个? ===')
SING=0x3B2BBE80
b=rd(SING,4)
print('  单例 [0x%08X] = 0x%08X' % (SING, struct.unpack('<I',b)[0]))
print('  => 单例用的是 0x00DC7274 (不是 0x00DC795C)')
print()
print('=== 所以: 闸门B(0x62FE80) 属于 0x00DC7274; 0x63C5E0 属于 0x00DC795C ===')
print('  两个 vtable 是不同类的! 两者关系需要重新确认')
