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
h=0x0810F7C0
print('=== dvar 3291 完整结构 (0x40 字节) ===')
b=rd(h,0x40)
for k in range(0,0x40,16):
    print('  +0x%02X  %s' % (k, b[k:k+16].hex(' ')))
print()
print('=== 逐字段 ===')
for k in range(0,0x20,4):
    v=struct.unpack_from('<I',b,k)[0]
    print('  +0x%02X = 0x%08X (%d)' % (k,v,v))
print()
print('=== 对照 dw_autoStartGame (0x0810AD88) 同样的布局 ===')
b2=rd(0x0810AD88,0x40)
for k in range(0,0x40,16):
    print('  +0x%02X  %s' % (k, b2[k:k+16].hex(' ')))
print()
for k in range(0,0x20,4):
    v=struct.unpack_from('<I',b2,k)[0]
    print('  +0x%02X = 0x%08X (%d)' % (k,v,v))
