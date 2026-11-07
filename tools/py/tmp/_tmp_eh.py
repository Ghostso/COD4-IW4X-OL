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
print('=== 找 vtable 0x00DC78F0 的实例(MyEventHandler 对象) ===')
pat=struct.pack('<I',0x00DC78F0)
i=img.find(pat,0); n=0
while i>=0:
    if covok(i):
        va=LO+i
        if not (0x00DC7800<=va<=0x00DC7A00):
            print('   实例候选 0x%08X  %s' % (va, img[max(0,i-8):i+24].hex(' ')))
            n+=1
    i=img.find(pat,i+1)
print('   共',n)
print()
print('=== 找 dwRoomMatch::Init 的引用/名字 ===')
# 搜 RTTI 名
for needle in (b'.?AVMyEventHandler@?5??Init@dwRoomMatch@@SAXXZ@', b'dwRoomMatch'):
    i=img.find(needle,0)
    if i>=0:
        print('  %r 在 0x%08X' % (needle[:40], LO+i))
        # 找它作为 TypeDescriptor 的引用
        td=LO+i-8  # pVFTable(4)+spare(4)
        pat2=struct.pack('<I',td)
        j=img.find(pat2,0); m=0
        while j>=0 and m<6:
            if covok(j): print('     TD 0x%08X 被引用于 0x%08X' % (td,LO+j)); m+=1
            j=img.find(pat2,j+1)
