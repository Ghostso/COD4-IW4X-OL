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
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
VT=0x00DC78F0
print('=== 所有引用 vtable 0x%08X 的位置(全内存, 不过滤) ===' % VT)
pat=struct.pack('<I',VT)
i=img.find(pat,0); n=0
while i>=0:
    if covok(i):
        va=LO+i
        seg='vtable区' if 0x00DC0000<=va<0x00DD0000 else ('代码' if 0x400000<=va<0x0EA59000 else '堆/数据')
        print('   0x%08X  %s   ctx=%s' % (va,seg,img[max(0,i-12):i+12].hex(' ')))
        n+=1
    i=img.find(pat,i+1)
print('   共',n)
print()
print('=== 所有引用 COL 0x00DF869C 的位置 ===')
pat=struct.pack('<I',0x00DF869C)
i=img.find(pat,0); n=0
while i>=0 and n<12:
    if covok(i):
        print('   0x%08X  ctx=%s' % (LO+i, img[max(0,i-10):i+10].hex(' ')))
        n+=1
    i=img.find(pat,i+1)
