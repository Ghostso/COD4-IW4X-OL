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
U=0x3ACA0CD8
print('=== 关键判据: 对象里有没有"每帧会被更新"的痕迹 ===')
print('  如果 0x63C5E0 在跑, 它至少会执行 0x63C7BD 的 call 0xB75DA0 (读 +0x138)')
print('  并调用 0xB75D80/0xB75D90 (timer 写)')
print()
print('=== 对比: dwRoomImp(确认在跑的) vs dwRoomMatchUber(可疑) ===')
I=0x3AB5F008
print('  dwRoomImp 0x%08X:' % I)
for off in (0x20,0x100,0x108,0x120,0x130,0x138,0x140):
    v=u32(I+off)
    print('     +0x%03X = %s' % (off, ('0x%08X'%v) if v is not None else '未覆盖'))
print('  dwRoomMatchUber 0x%08X:' % U)
for off in (0x20,0x100,0x108,0x120,0x130,0x138,0x140):
    v=u32(U+off)
    print('     +0x%03X = %s' % (off, ('0x%08X'%v) if v is not None else '未覆盖'))
print()
print('=== +0x68 是否在别处按 IVT 表分发 (找 vtable+0x68 的地址被引用) ===')
addr = 0x00DC795C+0x68
print('  vtable+0x68 的绝对地址 = 0x%08X (一般不会被直接引用)' % addr)
print()
print('=== 换个思路: 0x63C5E0 的兄弟槽 0x63C0C0/0x63C240 有无静态调用 ===')
for t,label in ((0x0063C5E0,'0x63C5E0'),(0x0063C0C0,'0x63C0C0'),(0x0063C240,'0x63C240'),(0x0063C9F0,'0x63C9F0')):
    n=0; calls=[]
    i=img.find(b'\xE8',0x400000-LO,0x0EA59000-LO)
    while i>=0:
        if all(cov[i+k]==1 for k in range(5)):
            rel=struct.unpack_from('<i',img,i+1)[0]
            if LO+i+5+rel==t: calls.append(LO+i)
        i=img.find(b'\xE8',i+1,0x0EA59000-LO)
    print('  %s 静态call数=%d %s' % (label,len(calls),[hex(c) for c in calls[:4]]))
