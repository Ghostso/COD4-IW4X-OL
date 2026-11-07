import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
def load(tag):
    img = open(os.path.join(D, tag+'.bin'),'rb').read()
    cov = open(os.path.join(D, tag+'_cover.bin'),'rb').read()
    return img, cov
img2, cov2 = load('snap_002')
print('snap_002 大小 %.1f MB, 覆盖 %.1f MB' % (len(img2)/1048576, sum(cov2)/1048576))
SING = 0x3B2BBE80
GATE = SING + 0x10614
o = GATE - LO
print('闸门B VA=0x%08X  覆盖=%s' % (GATE, cov2[o]))
print('闸门B 值 =', img2[o])
print()
print('=== 单例对象附近 (0x10600..0x10630) ===')
base = SING+0x10600-LO
for k in range(0,0x30,16):
    c = img2[base+k:base+k+16]
    print('  0x%08X  %-47s  %s' % (SING+0x10600+k, c.hex(' '), ''.join(chr(x) if 32<=x<=126 else '.' for x in c)))
print()
# 单例的 vtable 校验
vt = struct.unpack_from('<I', img2, SING-LO)[0]
print('单例 vtable = 0x%08X' % vt)
fn = struct.unpack_from('<I', img2, vt-LO+0x64)[0] if cov2[vt-LO+0x64] else None
print('vtable+0x64 = %s' % (('0x%08X'%fn) if fn else '未覆盖'))
if fn and cov2[fn-LO]:
    print('  函数体 =', img2[fn-LO:fn-LO+10].hex(' '))
