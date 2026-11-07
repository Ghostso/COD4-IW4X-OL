import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\FIXMC_20261027_140146'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def u32(va):
    b=rd(va,4); return struct.unpack('<I',b)[0] if b and len(b)==4 else None
U=0x3B169D98
print('=== 对象身份校验 ===')
vt=u32(U)
print('  vtable = 0x%08X (期望 0x00DC795C)' % (vt or 0))
if vt:
    print('  vtable+0x68 = 0x%08X (期望 0x0063C5E0)' % (u32(vt+0x68) or 0))
print()
print('=== 状态机 ===')
print('  [U+0x20] 状态 = %d  (1..5; 5=自动开局)' % (u32(U+0x20) or 0))
print()
print('=== 两个已知阻塞点 ===')
I=u32(0x082E13FC)
print('  阻塞1 闸门B = [dwRoomImp+0x10614] = %s' % (rd(I+0x10614,1)[0] if I and rd(I+0x10614,1) else '?'))
t=rd(U+0x138,8)
print('  阻塞2 计时器 [U+0x138] = %s' % (t.hex(' ') if t else '?'))
print()
print('=== 战斗服是否收到包 ===')
