import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
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
print('=== 修复后的两个阻塞点现状 ===')
print('  阻塞点1  闸门B = [dwRoomImp+0x10614] = %d   (由 dvar 3291 派生)' % (rd(0x3AB5F008+0x10614,1)[0]))
print('  阻塞点2  计时器 [dwRoomMatchUber+0x138] 8字节 = %s' % (rd(0x3ACA0CD8+0x138,8).hex(' ')))
print()
print('=== 检查: memberCount=1 之后 状态机推进到哪 ===')
U=0x3ACA0CD8
print('  [U+0x20] 状态 = %d' % (u32(U+0x20) or 0))
print('  [U+0x28] = %d' % (u32(U+0x28) or 0))
print('  [U+0x2C] = %d' % (u32(U+0x2C) or 0))
print()
print('=== 关键问题: 我们这次实验里, 客户端有没有尝试连 28960 ===')
