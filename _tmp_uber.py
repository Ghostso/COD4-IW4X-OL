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
def covok(i,n=4): return all(cov[i+k]==1 for k in range(n))
# 1) 找谁 call 构造函数 0x0063BCB0
print('=== call rel32 -> 0x0063BCB0 (dwRoomMatchUber 构造) ===')
n=0
i=img.find(b'\xE8', 0x400000-LO, 0x0EA59000-LO)
while i>=0:
    if covok(i,5):
        rel=struct.unpack_from('<i',img,i+1)[0]
        if LO+i+5+rel==0x0063BCB0:
            print('   0x%08X' % (LO+i)); n+=1
    i=img.find(b'\xE8',i+1,0x0EA59000-LO)
print('   共',n)
print()
# 2) 找堆/数据里 vtable == 0x00DC795C 的实例
print('=== 内存里 vtable==0x00DC795C 的对象 (dwRoomMatchUber 实例) ===')
pat=struct.pack('<I',0x00DC795C)
i=img.find(pat,0); n=0
while i>=0 and n<20:
    if covok(i):
        va=LO+i
        if not (0x00DC795C-0x100 <= va <= 0x00DC795C+0x100):  # 排除 vtable 自身/COL
            print('   对象候选 0x%08X' % va)
            b=img[max(0,i-8):i+40]
            print('      前后: %s' % b.hex(' '))
            n+=1
    i=img.find(pat,i+1)
print('   共',n)
