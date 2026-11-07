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
VT=0x00DC795C
print('=== dwRoomMatchUber vtable 0x%08X 里 0x63C5E0 的槽位 ===' % VT)
for off in range(0,0xA0,4):
    v=u32(VT+off)
    if v is None: continue
    mk='  <<< 0x63C5E0' if v==0x0063C5E0 else ''
    if off<0x30 or mk or v in (0x0063C0C0,0x0063C240,0x0063C9F0,0x0063CA00,0x0063CD30,0x0063CD90,0x0063CF90):
        print('  +0x%03X = 0x%08X%s' % (off,v,mk))
print()
print('=== 找 tick/update 类的槽 (通常是 +0x04 或 +0x08) ===')
for off in (0x00,0x04,0x08,0x0C):
    v=u32(VT+off)
    print('  +0x%02X = 0x%08X' % (off, v or 0))
print()
print('=== 关键: 0x63C5E0 是不是 \"tick/update\" 函数 ===')
print('  它读 [esi+0x20] 状态做跳表, 有 ret 无参, 典型 update/frame 函数特征')
print()
print('=== 谁调用 vtable+0x68 (即 0x63C5E0) ===')
import struct as st
# call [reg+0x68] = FF 90..97 68 00 00 00
for modrm in range(0x90,0x98):
    needle=bytes([0xFF,modrm])+st.pack('<I',0x68)
    i=img.find(needle,0x400000-LO,0x0EA59000-LO)
    n=0
    while i>=0 and n<8:
        if all(cov[i+k]==1 for k in range(6)):
            print('   0x%08X  %s' % (LO+i, needle.hex(' '))); n+=1
        i=img.find(needle,i+1,0x0EA59000-LO)
