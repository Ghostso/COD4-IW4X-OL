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
def cstr(va,n=140):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== 重要对照: dwRoomImp(存在的) 和 dwRoomMatachUber(不存在的) 的构造 ===')
print('  dwRoomImp      vtable 0x00DC7274  实例 0x3B2BBE80       ← 存在')
print('  dwRoomMatchUber vtable 0x00DC795C [0x82E1518]=0        ← 不存在')
print('  MyEventHandler  vtable 0x00DC78F0 实例 0               ← 不存在')
print()
print('=== dwRoomImp 的单例是谁创建的? 找写 [0x82E13FC] 的地方 ===')
pat=struct.pack('<I',0x082E13FC)
i=img.find(pat,0); n=0
while i>=0:
    if all(cov[i-LO+k]==1 for k in range(4)):
        va=LO+i
        if 0x400000<=va<0x0EA59000:
            print('   0x%08X  前4字节=%s' % (va, img[i-4:i].hex(' ')))
            n+=1
    i=img.find(pat,i+1)
print('   共',n)
