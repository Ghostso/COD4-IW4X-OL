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
def slot(vt, off):
    b=rd(vt+off,4)
    return struct.unpack('<I',b)[0] if b and len(b)==4 else None
print('=== 两个 vtable 的同类槽对比 ===')
print('  %-8s %-12s %-12s' % ('offset','0x00DC795C(基)','0x00DC7274(实测)'))
for off in (0x00,0x04,0x08,0x0C,0x10,0x14,0x18,0x1C,0x20,0x24,0x3C,0x5C,0x60,0x64,0xBC,0xC0,0xD0):
    a=slot(0x00DC795C,off); b=slot(0x00DC7274,off)
    same='  ← 相同' if a==b else ''
    print('  +0x%03X   %-12s %-12s%s' % (off, ('0x%08X'%a) if a else '?', ('0x%08X'%b) if b else '?', same))
print()
print('=== 基类 vtable 0x00DC795C 的 0x64 槽 ===')
v=slot(0x00DC795C,0x64)
print('  +0x64 = 0x%08X' % v if v else '  ?')
if v:
    b=rd(v,12)
    print('  函数体 =', b.hex(' ') if b else '未覆盖')
